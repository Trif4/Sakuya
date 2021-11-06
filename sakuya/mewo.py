from dataclasses import dataclass
import random
from typing import Dict

from discord import Guild
from discord.ext import commands
from discord.ext.commands import Bot

from .db import db, Guild as _Guild, Member as _Member


random_mewo = [
    "ME.. oh you're not mcmower.",
    "MEWO",
    "You didn't really expect me to say mewo did you"
]


@dataclass
class GuildState:
    guild: Guild
    mewo_enabled: bool


class Mewo(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.guilds: Dict[Guild, GuildState] = dict()
        self.data_loaded = False

    @commands.Cog.listener()
    async def on_ready(self):
        # This event fires on reconnects, but we only want it to run once
        if not self.data_loaded:
            self.data_loaded = True
            self.load_from_db()
            print('Mewo response ready.')

    def load_from_db(self):
        for g in db.query(_Guild).filter(_Guild.mewo_enabled.isnot(None)).all():
            guild: Guild = self.bot.get_guild(g.id)
            if guild:
                if g.mewo_enabled:
                    self.guilds[guild] = GuildState(guild=guild, mewo_enabled=True)
                else:
                    print(f"Mewo is not enabled on {guild.name}! Mewo responses disabled in guild.")
            else:
                print(f"Guild {g.id} not found during Mewo init.")

    @commands.command()
    async def mewo(self, ctx):
        state = self.guilds.get(ctx.guild)
        if state:

            memberid = ctx.message.mentions[0].id if len(ctx.message.mentions) == 1 else ctx.author.id

            member = db.query(_Member).get((memberid, ctx.guild.id)) or _Member(user_id=memberid,
                                                                                guild_id=ctx.guild.id)

            if member.mewo_text:
                msg = member.mewo_text
            else:
                msg = random.choice(random_mewo)
            
            await ctx.send(msg)
            return

    @commands.command()
    @commands.has_permissions(manage_nicknames=True)
    async def mewoset(self, ctx, *, mewo_text):
        state = self.guilds.get(ctx.guild)
        if state:

            if len(ctx.message.mentions) == 1:
                memberid = ctx.message.mentions[0].id
                mewo_text = str(mewo_text.split(" ",1)[1])
                pronoun = "their"
            else:
                memberid = ctx.author.id
                pronoun = "your"

            member = db.query(_Member).get((memberid, ctx.guild.id)) or _Member(user_id=memberid,
                                                                                guild_id=ctx.guild.id)
            previous_mewo = member.mewo_text

            try:
                if mewo_text.lower() == 'none' or mewo_text.lower() == 'clear':
                    msg = "No custom mewo anymore? Okay then.."
                    mewo_text = None
                elif previous_mewo:
                    msg = f"You want to change {pronoun} mewo? Okay I guess.."
                else:
                    msg = f"I have set {pronoun} mewo response."

                member.mewo_text = mewo_text
                db.add(member)
                db.commit()

                await ctx.send(msg)

            except (AssertionError) as e:
                await ctx.send("I'm terribly sorry, but I'm unable to do that at the moment. Please try again later.")
                print(e)

    async def enable(self, ctx):
        self.guilds[ctx.guild] = GuildState(guild=ctx.guild, mewo_enabled=True)
        g = db.query(_Guild).get(ctx.guild.id) or _Guild(id=ctx.guild.id)
        g.mewo_enabled = True
        db.add(g)
        db.commit()
        await ctx.send('Mewo responses enabled.')

    async def disable(self, ctx):
        del self.guilds[ctx.guild]
        g = db.query(_Guild).get(ctx.guild.id)
        g.mewo_enabled = False
        db.add(g)
        db.commit()
        await ctx.send('Mewo responses disabled.')

def setup(bot):
    bot.add_cog(Mewo(bot))
