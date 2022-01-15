import random
import string
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from typing import Dict

from discord import Guild, TextChannel, Member
from discord.ext import commands

from .db import db, Guild as _Guild


INVALID_GUESS_RESPONSES = [
    "I don't know that word, sorry. Try again.",
    "Now you're just making things up.",
    "I've checked every book in the mansion, and your word is in none of them. Try again.",
    "Never heard of it. Try again.",
    "What? Maybe you should try something else.",
    "Is this what commoners say these days..? I'll let you have another try.",
    "An original guess. Too original. Try again.",
    "Not a valid word. Try again.",
    "Is that supposed to be some kind of spell? Real words, please.",
    "Go to the library if you want to practice spell incantations.",
    "Bless you.",
    "No thanks. Try again."
]


with open('wordle/word_list.txt') as f:
    WORD_LIST = f.read().splitlines()

with open('wordle/valid_guesses.txt') as f:
    VALID_GUESSES = set(f.read().splitlines()) | set(WORD_LIST)

with open('wordle/emoji.txt') as f:
    EMOJI = f.read().splitlines()


def emojify_guess(guess, solution):
    letters = Counter(solution)
    result = [0]*5
    for i, letter in enumerate(guess):
        if solution[i] == letter:
            letters[letter] -= 1
            result[i] = 2
    for i, letter in enumerate(guess):
        if letters.get(letter):
            letters[letter] -= 1
            result[i] = 1
    return ''.join(EMOJI[string.ascii_lowercase.index(letter)+26*result[i]] for i, letter in enumerate(guess))


@dataclass
class GuildState:
    guild: Guild
    channel: TextChannel
    word: str = None
    date: date = None
    last_guess_at: datetime = datetime.utcfromtimestamp(0)
    guesses: list[str] = None
    guessers: set[Member] = None


class Wordle(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.guilds: Dict[Guild, GuildState] = dict()
        self.data_loaded = False

    @commands.Cog.listener()
    async def on_ready(self):
        # This event fires on reconnects, but we only want it to run once
        if not self.data_loaded:
            self.data_loaded = True
            self.load_from_db()
            print("Wordle module ready.")

    def load_from_db(self):
        for g in db.query(_Guild).filter(_Guild.wordle_channel_id.isnot(None)).all():
            guild: Guild = self.bot.get_guild(g.id)
            if guild:
                channel = guild.get_channel(g.wordle_channel_id)
                if channel:
                    if channel.permissions_for(guild.me).send_messages:
                        self.guilds[guild] = GuildState(guild=guild, channel=channel)
                    else:
                        print(f"Missing permissions for Wordle channel in {guild.name}. Wordle disabled in guild.")
                else:
                    print(f"Wordle channel doesn't exist in {guild.name}. Wordle disabled in guild.")
            else:
                print(f"Guild {g.id} not found during Wordle init.")

    @commands.command()
    async def guess(self, ctx: commands.Context, guess: str):
        state = self.guilds.get(ctx.guild)
        if not (state and ctx.channel == state.channel) or (datetime.utcnow() - state.last_guess_at).seconds < 3:
            # Second condition prevents accidental simultaneous guesses by multiple players
            return
        if not guess or len(guess) != 5 or any(l not in string.ascii_letters for l in guess):
            await ctx.send("Your guess must be 5 letters, a-z only.")
            return
        guess = guess.lower()
        if state.date != date.today():
            state.word = random.choice(WORD_LIST)
            state.guesses = []
            state.guessers = set()
            state.date = date.today()
        if len(state.guesses) == 6 or (len(state.guesses) and state.guesses[-1] == state.word):
            await ctx.send("Game's over for today. Come play again tomorrow!")
            return
        if ctx.author in state.guessers:
            await ctx.send("It's more fun if everyone gets to guess. Please come play again tomorrow, though!")
            return
        if guess not in VALID_GUESSES:
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

        guess_count_text = 'X' if game_state == 'lost' else str(len(state.guesses))
        msg = f"**Wordle** - {guess_count_text}/6\n"
        msg += "\n".join(emojify_guess(g, state.word) for g in state.guesses)
        msg += "\n\n"
        match game_state:
            case 'won':
                msg += [
                    "...wait, huh? You possess mysterious abilities.",
                    "Excellent! Your skills of deduction are impressive.",
                    "Well done!",
                    "Not bad.",
                    "You won!",
                    "I was worried I made it too difficult. Good job."
                ][len(state.guesses)-1]
                msg += "\nCome play again tomorrow."
            case 'lost':
                msg += f"You lost. The word was **{state.word.upper()}**."
                msg += "\nTry again tomorrow."
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
            print(f"Tried to enable Wordle in {ctx.guild.name}, but missing permissions in channel.")
            return
        self.guilds[ctx.guild] = GuildState(guild=ctx.guild, channel=ctx.channel)
        g = db.query(_Guild).get(ctx.guild.id) or _Guild(id=ctx.guild.id)
        g.wordle_channel_id = ctx.channel.id
        db.add(g)
        db.commit()
        await ctx.send('Wordle game enabled for this channel. Start guessing with "Maid, guess [word]".')

    async def disable(self, ctx: commands.Context):
        del self.guilds[ctx.guild]
        g = db.query(_Guild).get(ctx.guild.id)
        g.wordle_channel_id = None
        db.add(g)
        db.commit()
        await ctx.send('Wordle game disabled.')


def setup(bot: commands.Bot):
    bot.add_cog(Wordle(bot))
