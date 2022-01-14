from discord import TextChannel
from discord.ext import commands


class Settings(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.group()
    async def enable(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('Enable what?')

    @enable.command(name='sentinel')
    @commands.has_guild_permissions(ban_members=True)
    async def enable_sentinel(self, ctx, *, alert_channel: TextChannel = None):
        await self.bot.get_cog('Sentinel').enable(ctx, alert_channel)

    @commands.group()
    async def disable(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('Disable what? You?')

    @disable.command(name='sentinel')
    @commands.has_guild_permissions(ban_members=True)
    async def disable_sentinel(self, ctx):
        await self.bot.get_cog('Sentinel').disable(ctx)


def setup(bot: commands.Bot):
    bot.add_cog(Settings(bot))
