from dataclasses import dataclass
import random
from typing import Dict

from discord import Guild, TextChannel
from discord.ext import commands
from discord.ext.commands import Bot
from mcrcon import MCRcon, MCRconException

from .db import db, Guild as _Guild, Member as _Member


trust_messages = [
    "Play nice!",
    "I'll be watching you.",
    "Please follow the rules.",
    "Don't make me clean up after you.",
    "Tread carefully.",
    "I pray that you won't prove my trust misplaced.",
    "By the way, when are they adding knives..?",
    "Take care.",
    "I won't help you find diamonds, though.",
    "Please respect the staff."
]


@dataclass
class GuildState:
    guild: Guild
    channel: TextChannel
    rcon_address: str
    rcon_pass: str


class Minecraft(commands.Cog):
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
            print('Minecraft configuration loaded.')

    def load_from_db(self):
        for g in db.query(_Guild).filter(_Guild.minecraft_channel_id.isnot(None)).all():
            guild: Guild = self.bot.get_guild(g.id)
            if guild:
                channel = guild.get_channel(g.minecraft_channel_id)
                if channel:
                    if channel.permissions_for(guild.me).send_messages:
                        self.guilds[guild] = GuildState(
                            guild=guild,
                            channel=channel,
                            rcon_address=g.minecraft_rcon_address,
                            rcon_pass=g.minecraft_rcon_pass
                        )
                    else:
                        print(f"Missing permissions for Minecraft channel in {guild.name}! Module disabled for guild.")
                else:
                    print(f"Minecraft channel doesn't exist in {guild.name}! Module disabled for guild.")
            else:
                print(f"Guild {g.id} not found during Minecraft init.")

    @commands.command()
    async def whitelist(self, ctx, username):
        state = self.guilds.get(ctx.guild)
        if state and ctx.channel is state.channel:
            if len(ctx.author.roles) == 0:
                await ctx.send(f'Sorry, we only just met. Talk to me once you have a role.')
                return

            member = db.query(_Member).get((ctx.author.id, ctx.guild.id)) or _Member(user_id=ctx.author.id,
                                                                                     guild_id=ctx.guild.id)
            previous_username = member.minecraft_username

            try:
                with MCRcon(state.rcon_address, state.rcon_pass) as rcon:
                    if previous_username:
                        rcon.command(f'whitelist remove {previous_username}')
                    res = rcon.command(f'whitelist add {username}')
                    print(res)
                    assert ('Added' in res or 'already whitelisted' in res)

                member.minecraft_username = username
                db.add(member)
                db.commit()

                if previous_username:
                    msg = f"Hmm... I already whitelisted '{previous_username}' for you earlier, though. "
                    msg += f"Oh well, I'll remove that username and add '{username}' instead. "
                else:
                    msg = "I have added you to the whitelist. "
                msg += random.choice(trust_messages)
                await ctx.send(msg)

            except (MCRconException, ConnectionError, AssertionError) as e:
                await ctx.send("I'm terribly sorry, but I'm unable to do that at the moment. Please try again later.")
                print(e)


def setup(bot):
    bot.add_cog(Minecraft(bot))
