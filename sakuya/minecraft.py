from dataclasses import dataclass
import logging
import random
from typing import Dict

import discord
from discord.ext import commands
from mcrcon import MCRcon, MCRconException
from sqlalchemy import select

from .db import Session, Guild, Member


TRUST_MESSAGES = [
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

logger = logging.getLogger(__name__)


@dataclass
class GuildState:
    guild: Guild
    channel: discord.TextChannel
    rcon_address: str
    rcon_pass: str


class Minecraft(commands.Cog):
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
            logger.info('Minecraft configuration loaded.')

    async def load_from_db(self):
        async with Session() as session:
            query = select(Guild).where(Guild.minecraft_channel_id.isnot(None))
            guilds = (await session.scalars(query)).all()
        for g in guilds:
            guild = self.bot.get_guild(g.id)
            if not guild:
                logger.warning(f"Guild {g.id} not found during Minecraft init.")
                continue
            channel = guild.get_channel(g.minecraft_channel_id)
            if not channel:
                logger.warning(f"Minecraft channel doesn't exist in {guild.name}! Module disabled for guild.")
                continue
            if not channel.permissions_for(guild.me).send_messages:
                logger.warning(f"Missing permissions for Minecraft channel in {guild.name}! Module disabled for guild.")
                continue
            self.guilds[guild] = GuildState(
                guild=guild,
                channel=channel,
                rcon_address=g.minecraft_rcon_address,
                rcon_pass=g.minecraft_rcon_pass
            )

    @commands.command()
    async def whitelist(self, ctx, username):
        state = self.guilds.get(ctx.guild)
        if not state or ctx.channel != state.channel:
            return
        if len(ctx.author.roles) == 1:  # every member has @everyone
            await ctx.send(f'Sorry, we only just met. Talk to me once you have a role.')
            return

        async with Session.begin() as session:
            member = session.get(
                Member, (ctx.author.id, ctx.guild.id)
            ) or Member(user_id=ctx.author.id, guild_id=ctx.guild.id)
            previous_username = member.minecraft_username

            try:
                with MCRcon(state.rcon_address, state.rcon_pass) as rcon:
                    if previous_username:
                        logger.info(f'Removing "{previous_username}" from whitelist (replacing with new username)')
                        res = rcon.command(f'whitelist remove {previous_username}')
                        logger.info(f'Server response: {res}')
                    logger.info(f'Adding {username} to whitelist')
                    res = rcon.command(f'whitelist add {username}')
                    logger.info(f'Server response: {res}')
                    assert ('Added' in res or 'already whitelisted' in res)

                member.minecraft_username = username
                session.add(member)

                if previous_username:
                    msg = f"Hmm... I already whitelisted '{previous_username}' for you earlier, though. "
                    msg += f"Oh well, I'll remove that username and add '{username}' instead. "
                else:
                    msg = "I have added you to the whitelist. "
                msg += random.choice(TRUST_MESSAGES)
                await ctx.send(msg)

            except (MCRconException, ConnectionError, AssertionError) as e:
                await ctx.send("I'm terribly sorry, but I'm unable to do that at the moment. Please try again later.")
                logger.error(e)


async def setup(bot: commands.Bot):
    await bot.add_cog(Minecraft(bot))
