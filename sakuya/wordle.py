import itertools
import logging
import os
import random
import re
import string
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Dict, Type

import discord
from discord.ext import commands
import emoji
from sqlalchemy import select
import wordninja

from .db import Session, Guild


GAMES_PER_DAY = 3
GAME_TIMEDELTA = timedelta(minutes=1440/GAMES_PER_DAY)
BONUS_GAME_THRESHOLD = 2
INVALID_GUESS_RESPONSES = [
    "I don't know that word, sorry. Try again.",
    "Now you're just making things up.",
    "I've checked every book in the mansion, and your word is in none of them. Try again.",
    "Never heard of it. Try again.",
    "What? Maybe you should try something else.",
    "Is this what commoners say these days..? I'll let you have another try.",
    "Not a valid word. Try again.",
    "Is that supposed to be some kind of spell?",
    "Go to the library if you want to practice spell incantations.",
    "I'm not sure I know what you mean. Try again.",
    "English only, please."
]
DISCORD_EMOTE_REGEX = re.compile(r'<a?:(\w+):\d+>', re.ASCII)

logger = logging.getLogger(__name__)


with open('wordle/word_list.txt') as f:
    WORD_LIST = f.read().splitlines()

with open('wordle/valid_guesses.txt') as f:
    VALID_GUESSES = set(f.read().splitlines()) | set(WORD_LIST)

with open('wordle/emoji.txt') as f:
    EMOJI = f.read().splitlines()


def current_game_start():
    midnight = datetime.combine(datetime.utcnow(), time.min)
    start_times = [midnight + GAME_TIMEDELTA*i for i in range(GAMES_PER_DAY)]
    return max(st for st in start_times if st <= datetime.utcnow())


def time_until_next_game():
    next_start = current_game_start() + GAME_TIMEDELTA
    duration = next_start - datetime.utcnow()
    hours, remainder = divmod(duration.total_seconds(), 3600)
    minutes = remainder // 60
    return f'{int(hours)}h{int(minutes):02}m'


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
        return {self.value.lower()}


def segmentize_guess(guess: str) -> list[GuessSegment]:
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
    for s in segments_partial:
        if isinstance(s, str):
            segments.extend(segmentize(
                s,
                [(m.start(), m.end(), DiscordEmoteGuessSegment(m.group(1)))
                 for m in DISCORD_EMOTE_REGEX.finditer(s)],
                StringGuessSegment
            ))
        else:
            segments.append(s)

    return segments


class GuessLengthError(Exception):
    """Raised when a guess is not 5 letters long."""
    pass


class InvalidGuessError(Exception):
    """Raised when a guess has the correct length but cannot be found in the valid words dictionary."""
    pass


def parse_guess(guess):
    """Returns a valid guess. Guesses are parsed using the patented GuessGPT Emoji AI Interpretation Engine™.

    Raises `GuessLengthError` when no guess of the correct length can be found.
    Raises `InvalidGuessError` when no guess in the valid words dictionary can be found.
    """
    if not guess:
        raise GuessLengthError

    segments = segmentize_guess(guess)
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
    return ''.join(EMOJI[string.ascii_lowercase.index(letter)+26*result[i]] for i, letter in enumerate(guess))


@dataclass
class GuildState:
    guild: discord.Guild
    channel: discord.TextChannel
    word: str = None
    game_start: datetime = None
    last_guess_at: datetime = datetime.utcfromtimestamp(0)
    guesses: list[str] = None
    guessers: set[discord.Member] = None

    def started(self):
        return self.word is not None and self.guesses is not None

    def finished(self):
        return self.started() and len(self.guesses) == 6 or (len(self.guesses) and self.guesses[-1] == self.word)


class Wordle(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.guilds: Dict[discord.Guild, GuildState] = dict()
        self.data_loaded = False

    @commands.Cog.listener()
    async def on_ready(self):
        # This event fires on reconnects, but we only want it to run once
        if not self.data_loaded:
            self.data_loaded = True
            await self.load_from_db()
            logger.info("Wordle module ready.")

    async def load_from_db(self):
        async with Session() as session:
            query = select(Guild).where(Guild.wordle_channel_id.isnot(None))
            guilds = (await session.scalars(query)).all()
        for g in guilds:
            guild = self.bot.get_guild(g.id)
            if not guild:
                logger.warning(f"Guild {g.id} not found during Wordle init.")
                return
            channel = guild.get_channel(g.wordle_channel_id)
            if not channel:
                logger.warning(f"Wordle channel doesn't exist in {guild.name}. Wordle disabled in guild.")
                return
            if not channel.permissions_for(guild.me).send_messages:
                logger.warning(f"Missing permissions for Wordle channel in {guild.name}. Wordle disabled in guild.")
                return
            self.guilds[guild] = GuildState(guild=guild, channel=channel)

    def reset(self, guild: discord.Guild):
        self.guilds[guild] = GuildState(guild=guild, channel=self.guilds[guild].channel)

    @commands.command()
    async def guess(self, ctx: commands.Context, *guess: str):
        state = self.guilds.get(ctx.guild)
        if not (state and ctx.channel == state.channel) or (datetime.utcnow() - state.last_guess_at).seconds < 3:
            # Second condition prevents accidental simultaneous guesses by multiple players
            return
        if state.game_start != current_game_start():
            if state.started() and not state.finished():
                # Last game wasn't finished before the reset
                last_word = state.word
                self.reset(state.guild)
                await ctx.send(f"Time's up! The word was **{last_word.upper()}**.\nPlease try again.")
                return
            if os.getenv('SAKUYA_DEBUG'):
                state.word = 'debug'
            else:
                state.word = random.choice(WORD_LIST)
            state.game_start = current_game_start()
            state.guesses = []
            state.guessers = set()
        if state.finished():
            await ctx.send(f"I'm preparing for the next game. Come back in {time_until_next_game()}!")
            return
        if ctx.author in state.guessers and not os.getenv('SAKUYA_DEBUG'):
            await ctx.send("It's more fun if everyone gets to guess. Please come play again later, though!")
            return

        # Guess parsing
        if guess and len(guess[0]) == 5:
            # The first word has the right length for a guess; use that and ignore potential silly jokes after it
            guess = guess[0]
        else:
            # We're receiving the guess as a list to cover cases where Discord inserted spaces between emoji
            guess = ''.join(guess)
        try:
            guess = parse_guess(guess)
        except GuessLengthError:
            await ctx.send("Your guess must be 5 letters, a-z only.")
            return
        except InvalidGuessError:
            await ctx.send(random.choice(INVALID_GUESS_RESPONSES))
            return
        if guess in state.guesses:
            await ctx.send("Someone else already guessed that. Try again.")
            return

        # Finally done validating. Process the guess!
        state.guesses.append(guess)
        state.guessers.add(ctx.author)
        state.last_guess_at = datetime.utcnow()

        if guess == state.word:
            game_state = 'won'
        elif len(state.guesses) == 6:
            game_state = 'lost'
        else:
            game_state = 'playing'

        guess_count = len(state.guesses)
        guess_count_text = 'X' if game_state == 'lost' else str(guess_count)
        msg = f"**Wordle** - {guess_count_text}/6\n"
        msg += "\n".join(emojify_guess(g, state.word) for g in state.guesses)
        msg += "\n\n"
        match game_state:
            case 'won':
                msg += [
                    "...wait, huh? You possess mysterious abilities.",
                    "Excellent! It seems luck is on your side today.",
                    "Well done!",
                    "Not bad.",
                    "You won!",
                    "I was worried I made it too difficult. Good job."
                ][guess_count-1]
                if guess_count <= BONUS_GAME_THRESHOLD:
                    msg += "\nCare for an extra round? I've got more time to play since you were so quick."
                    self.reset(state.guild)
                else:
                    msg += f"\nNext game will be ready in {time_until_next_game()}."
            case 'lost':
                msg += f"You lost. The word was **{state.word.upper()}**."
                msg += f"\nNext game will be ready in {time_until_next_game()}."
            case 'playing':
                msg += "Available letters:\n"
                guessed_letters = {letter for guess in state.guesses for letter in guess}
                highlighting = False
                for letter in string.ascii_lowercase:
                    if letter in guessed_letters:
                        if letter in state.word:
                            if not highlighting:
                                msg += "**"
                                highlighting = True
                            msg += letter
                    else:
                        if highlighting:
                            msg += "**"
                            highlighting = False
                        msg += letter
                if highlighting:
                    msg += "**"
        await ctx.send(msg)

    async def enable(self, ctx: commands.Context):
        if not ctx.channel.permissions_for(ctx.me).send_messages:
            logger.warning(f"Tried to enable Wordle in {ctx.guild.name}, but missing permissions in channel.")
            return
        self.guilds[ctx.guild] = GuildState(guild=ctx.guild, channel=ctx.channel)
        async with Session.begin() as session:
            g = await session.get(Guild, ctx.guild.id) or Guild(id=ctx.guild.id)
            g.wordle_channel_id = ctx.channel.id
            session.add(g)
        await ctx.send('Wordle game enabled for this channel. Start guessing with "Maid, guess [word]".')

    async def disable(self, ctx: commands.Context):
        del self.guilds[ctx.guild]
        async with Session.begin() as session:
            g = await session.get(Guild, ctx.guild.id)
            g.wordle_channel_id = None
        await ctx.send('Wordle game disabled.')


async def setup(bot: commands.Bot):
    await bot.add_cog(Wordle(bot))
