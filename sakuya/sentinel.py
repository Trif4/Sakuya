from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict

from discord import Guild, TextChannel, Member
from discord.ext import commands
from discord.ext.commands import Bot

from .db import db, Guild as _Guild


SUSPICIOUS_ACCOUNT_AGE_LIMIT_DAYS = 7
ALERT_RESET_MINUTES = 15


@dataclass
class GuildState:
    guild: Guild
    alert_channel: TextChannel
    last_alert: datetime = None
    recent_alerts: int = 0


class Sentinel(commands.Cog):
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
            print('Sentinel ready.')

    def load_from_db(self):
        for g in db.query(_Guild).filter(_Guild.sentinel_channel_id.isnot(None)).all():
            guild: Guild = self.bot.get_guild(g.id)
            if guild:
                channel = guild.get_channel(g.sentinel_channel_id)
                if channel:
                    self.guilds[guild] = GuildState(guild=guild, alert_channel=channel)
                else:
                    print(f"Alert channel doesn't exist in {guild.name}! Sentinel disabled.")
            else:
                print(f"Guild {g.id} not found during Sentinel init.")

    @commands.Cog.listener()
    async def on_member_join(self, member: Member):
        state = self.guilds.get(member.guild)
        if state:
            # Guild has sentinel enabled
            now = datetime.now()
            account_age = now - member.created_at
            if account_age.days < SUSPICIOUS_ACCOUNT_AGE_LIMIT_DAYS:
                # Update state
                if state.last_alert and now - state.last_alert > timedelta(minutes=ALERT_RESET_MINUTES):
                    # It's been quiet for a while, reset counter
                    state.recent_alerts = 0
                state.last_alert = now
                state.recent_alerts += 1

                # Alert
                if state.recent_alerts <= 3:
                    msg = f'Suspicious user {member.mention} joined the server (account {account_age.days} days old).'
                    if state.recent_alerts == 3:
                        msg += "\nI believe we are being raided. I will silence further alerts until things have been "
                        msg += f"calm for {ALERT_RESET_MINUTES} minutes."
                    await state.alert_channel.send(msg)

    async def enable(self, ctx, alert_channel: TextChannel = None):
        channel = alert_channel or ctx.channel
        self.guilds[ctx.guild] = GuildState(guild=ctx.guild, alert_channel=channel)
        g = db.query(_Guild).get(ctx.guild.id) or _Guild(id=ctx.guild.id)
        g.sentinel_channel_id = channel.id
        db.add(g)
        db.commit()
        await ctx.send(f'Sentinel mode enabled. I will keep watch and report in {channel.mention}.')

    async def disable(self, ctx):
        del self.guilds[ctx.guild]
        g = db.query(_Guild).get(ctx.guild.id)
        g.sentinel_channel_id = None
        db.add(g)
        db.commit()
        await ctx.send('Sentinel mode disabled.')


def setup(bot):
    bot.add_cog(Sentinel(bot))
