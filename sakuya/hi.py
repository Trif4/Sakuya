from discord.ext import commands


@commands.command()
@commands.is_owner()
async def hi(ctx, _):
    await ctx.send('Hi, master!')


def setup(bot):
    bot.add_command(hi)
