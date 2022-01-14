from discord.ext import commands


class Hewo(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        if await self.bot.is_owner(message.channel.guild.owner) and (hewos := message.content.lower().count('hewo')):
            await message.channel.send('HEWO ' * hewos)


def setup(bot: commands.Bot):
    bot.add_cog(Hewo(bot))
