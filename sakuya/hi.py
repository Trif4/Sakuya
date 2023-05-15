from discord.ext import commands


@commands.command()
@commands.is_owner()
async def hi(ctx):
    await ctx.send('Hi, master!')


async def setup(bot: commands.Bot):
    bot.add_command(hi)
