from discord.ext import commands

from .game import Wordle


async def setup(bot: commands.Bot):
    await bot.add_cog(Wordle(bot))
