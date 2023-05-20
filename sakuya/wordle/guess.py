import itertools
import re
import string
from collections import Counter
from typing import Type

import emoji
import wordninja

from .data import LETTER_EMOTES, VALID_GUESSES


class GuessSegment:
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f'<{self.__class__.__name__}: "{self.value}">'

    @property
    def _aliases(self) -> set[str]:
        return {self.value}

    def explode(self) -> set[str]:
        values = self._aliases.union(*(wordninja.split(a) for a in self._aliases))
        # Very naively attempt to add singular versions of plural nouns
        # We could use a library, but players probably don't expect e.g. "women" to turn into "woman", so this will do
        values |= {v[:-1] for v in values if v and v[-1] == 's'}
        # Strip out any special characters and lowercase
        values = {re.sub('[^a-z]+', '', v.lower()) for v in values}
        return values


class EmojiGuessSegment(GuessSegment):
    @property
    def _aliases(self) -> set[str]:
        data = emoji.EMOJI_DATA.get(self.value)
        if not data:
            return {''}
        return {data['en']} | set(data.get('alias', []))


class DiscordEmoteGuessSegment(GuessSegment):
    pass


class StringGuessSegment(GuessSegment):
    def explode(self) -> set[str]:
        # Regular text in guesses should be left as is
        return {self.value.lower()}


class GuessLengthError(Exception):
    """Raised when a guess is not 5 letters long."""
    pass


class InvalidGuessError(Exception):
    """Raised when a guess has the correct length but cannot be found in the valid words dictionary."""
    pass


def _segmentize_guess(guess: str) -> list[GuessSegment]:
    def segmentize(
            text, matches: list[tuple[int, int, GuessSegment]], nonmatch_class: Type[str | StringGuessSegment]
    ) -> list[str | GuessSegment]:
        segments = []
        pos = 0
        for start, end, matched in matches:
            if start > pos:
                segments.append(nonmatch_class(text[pos:start]))
            segments.append(matched)
            pos = end
        if pos < len(text):
            segments.append(nonmatch_class(text[pos:]))
        return segments

    # First, split into segments of regular emoji & "unprocessed" strings
    emoji_matches = [(m['match_start'], m['match_end'], EmojiGuessSegment(m['emoji'])) for m in emoji.emoji_list(guess)]
    segments_partial = segmentize(guess, emoji_matches, str)

    # Now split unprocessed strings into Discord emote segments & string segments
    segments = []
    discord_emote_regex = re.compile(r'<a?:(\w+):\d+>', re.ASCII)
    for s in segments_partial:
        if isinstance(s, str):
            segments.extend(segmentize(
                s,
                [(m.start(), m.end(), DiscordEmoteGuessSegment(m.group(1)))
                 for m in discord_emote_regex.finditer(s)],
                StringGuessSegment
            ))
        else:
            segments.append(s)

    return segments


def parse_guess(guess):
    """Returns a valid guess. Guesses are parsed using the patented GuessGPT Emoji AI Interpretation Engine™.

    Raises `GuessLengthError` when no guess of the correct length can be found.
    Raises `InvalidGuessError` when no guess in the valid words dictionary can be found.
    """
    if not guess:
        raise GuessLengthError

    segments = _segmentize_guess(guess)
    if len(segments) > 5:
        raise GuessLengthError

    # Emotes & emoji often have multiple possible interpretations, so first we generate every possible combination
    interpretations = ["".join(i) for i in itertools.product(*[s.explode() for s in segments])]
    if not any(len(i) == 5 for i in interpretations):
        raise GuessLengthError
    # Then filter out interpretations that aren't valid guesses anyway
    interpretations = [i for i in interpretations if i in VALID_GUESSES]
    if not interpretations:
        raise InvalidGuessError

    # Finally, pick the interpretation that's the most specific (determined by word cost)
    # This means that e.g. the "woman_pilot" emoji gets interpreted as "pilot" rather than "woman"
    return max(interpretations, key=lambda i: wordninja.DEFAULT_LANGUAGE_MODEL._wordcost.get(i, 999))


def emojify_guess(guess, solution):
    """Formats a guess as grey/yellow/green letter emotes."""
    letters = Counter(solution)
    result = [0]*5
    for i, letter in enumerate(guess):
        if solution[i] == letter:
            letters[letter] -= 1
            result[i] = 2
    for i, letter in enumerate(guess):
        if solution[i] != letter and letters.get(letter):
            letters[letter] -= 1
            result[i] = 1
    return ''.join(LETTER_EMOTES[string.ascii_lowercase.index(letter) + 26 * result[i]] for i, letter in enumerate(guess))
