import itertools
import re
import string
from collections import Counter
from collections.abc import Sequence
from typing import Type

import emoji
import wordninja

from .data import LETTER_EMOTES, VALID_GUESSES


class GuessSegment:
    value: str

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f'<{self.__class__.__name__}: "{self.value}">'

    @property
    def _aliases(self) -> set[str]:
        return {self.value}

    def explode(self) -> set[str]:
        # Find meaningful substrings within aliases based on capitalisation, underscores, and word frequency analysis
        values = self._aliases.union(
            *(re.findall(r'[a-zA-Z][^A-Z_]*', a) for a in self._aliases),
            *(re.findall(r'[A-Z+][^a-z_$]+', a) for a in self._aliases),
            *(wordninja.split(a) for a in self._aliases)
        )
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


class CustomGuessSegment(GuessSegment):
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


DISCORD_EMOTE_REGEX = re.compile(r'<a?:(\w+):\d+>', re.ASCII)
# Markdown escapes (backslashes) may occur before any character.
SHRUG_REGEX = re.compile(''.join(r'\\?' + re.escape(char) for char in r'¯\_(ツ)_/¯'))


def _segmentize_guess(guess: str) -> list[GuessSegment]:
    def segmentize(
            text, matches: Sequence[tuple[int, int, GuessSegment]], nonmatch_class: Type[str | StringGuessSegment]
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
    for s in segments_partial:
        if isinstance(s, str):
            segments.extend(segmentize(
                s,
                [(m.start(), m.end(), DiscordEmoteGuessSegment(m.group(1)))
                 for m in DISCORD_EMOTE_REGEX.finditer(s)],
                str
            ))
        else:
            segments.append(s)

    # Finally, add any custom matches we might have
    segments_partial = segments
    segments = []
    for s in segments_partial:
        if isinstance(s, str):
            segments.extend(segmentize(
                s,
                [(m.start(), m.end(), CustomGuessSegment('shrug'))
                 for m in SHRUG_REGEX.finditer(s)],
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

    # Finally, pick the interpretation that we think the player wanted
    if len(segments) == 1:
        # If the guess is an emoji, the entire guess is contained within it.
        # The player most likely wants the most specific word, i.e. "woman_pilot" -> "pilot".
        return max(interpretations, key=lambda i: wordninja.DEFAULT_LANGUAGE_MODEL._wordcost.get(i, 999))
    else:
        # The guess is a combination, so no single emoji contains the whole guess.
        # The player most likely wants the most obvious word, so avoid picking obscure interpretations.
        return min(interpretations, key=lambda i: wordninja.DEFAULT_LANGUAGE_MODEL._wordcost.get(i, 999))


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
