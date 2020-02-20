from discord.ext import commands

from .client import client


@client.command()
@commands.is_owner()
async def hi(ctx, _):
    await ctx.send('Hi, master!')
