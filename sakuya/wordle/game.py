import logging
import os
import random
import string
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from typing import Dict

import discord
from discord.ext import commands
from sqlalchemy import select

from sakuya.db import Session, Guild
from .data import WORD_LIST
from .guess import GuessLengthError, InvalidGuessError, emojify_guess, parse_guess


FREE_PLAY = False  # no wait between rounds, multiple guesses per player
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

logger = logging.getLogger(__package__)


def current_game_start():
    midnight = datetime.combine(datetime.utcnow(), time.min, timezone.utc)
    start_times = [midnight + GAME_TIMEDELTA*i for i in range(GAMES_PER_DAY)]
    return max(st for st in start_times if st <= datetime.now(timezone.utc))


def time_until_next_game():
    next_start = current_game_start() + GAME_TIMEDELTA
    absolute_time = discord.utils.format_dt(next_start, 't')
    relative_time = discord.utils.format_dt(next_start, 'R')
    return f'{absolute_time} ({relative_time})'


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
                continue
            channel = guild.get_channel_or_thread(g.wordle_channel_id)
            if not channel:
                logger.warning(f"Wordle channel doesn't exist in {guild.name}. Wordle disabled in guild.")
                continue
            if not channel.permissions_for(guild.me).send_messages:
                logger.warning(f"Missing permissions for Wordle channel in {guild.name}. Wordle disabled in guild.")
                continue
            self.guilds[guild] = GuildState(guild=guild, channel=channel)

    def reset(self, guild: discord.Guild):
        self.guilds[guild] = GuildState(guild=guild, channel=self.guilds[guild].channel)

    @commands.command()
    async def guess(self, ctx: commands.Context, *guess: str):
        state = self.guilds.get(ctx.guild)
        overtime = False
        if not (state and ctx.channel == state.channel) or (datetime.now() - state.last_guess_at).total_seconds() < 3:
            # Second condition prevents accidental simultaneous guesses by multiple players
            return
        if state.game_start != current_game_start():
            if state.started() and not state.finished():
                overtime = True
            else:
                # Start a new game
                if os.getenv('SAKUYA_DEBUG'):
                    state.word = 'debug'
                else:
                    state.word = random.choice(WORD_LIST)
                state.game_start = current_game_start()
                state.guesses = []
                state.guessers = set()
        if state.finished():
            await ctx.send(f"I'm preparing for the next game. Come back at {time_until_next_game()}!")
            return
        if ctx.author in state.guessers and not (overtime or FREE_PLAY or os.getenv('SAKUYA_DEBUG')):
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
            await ctx.send("Someone already guessed that. Try again.")
            return

        # Finally done validating. Process the guess!
        state.guesses.append(guess)
        state.guessers.add(ctx.author)
        state.last_guess_at = datetime.now()

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
                if FREE_PLAY:
                    msg += "\nI've got lots of time today, so play all you want."
                    self.reset(state.guild)
                elif guess_count <= BONUS_GAME_THRESHOLD:
                    msg += "\nCare for an extra round? I've got more time to play since you were so quick."
                    self.reset(state.guild)
                elif overtime:
                    msg += "\nWould you like to play some more? I've already prepared the next round."
                else:
                    msg += f"\nNext game will be ready at {time_until_next_game()}."
            case 'lost':
                msg += f"You lost. The word was **{state.word.upper()}**."
                if FREE_PLAY:
                    msg += "\nI've got lots of time today, so play all you want."
                    self.reset(state.guild)
                elif overtime:
                    msg += "\nCare to give it another try? I've got a new word ready for you."
                else:
                    msg += f"\nNext game will be ready at {time_until_next_game()}."
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
                if overtime:
                    msg += "\nI'd like to finish this round soon, so feel free to guess multiple times."
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
