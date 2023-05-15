import random

from discord.ext import commands


# Hello GitHub enjoyer! Don't tell anyone I added this.
RARE_HEWOS = [
    "Greetings!",
    "Bonjour!",
    "BYE",
    "SAYONARA",
    "WOHE",
    "MEWO",
    "HEW--\\*cough\\* sorry. cold.",
    "NYA",
    "ヘヲ",
    "heWO",
    "HEW0",
    "\\*stab\\*",
    "Gesundheit.",
    "'C:\\Sakuya\\cmd\\hewo.exe' is not recognized as an internal or external command, operable program or batch file.",
    "HEEEEEEEEEEEEEEEEEEE WO!!!!!!!!!!!!",
    "Yahaha! You found me!",
    "dQw4w9WgXcQ",
    "the game",
]


class Hewo(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        if await self.bot.is_owner(message.channel.guild.owner) and (hewos := message.content.lower().count('hewo')):
            if random.random() > 0.99:
                await message.channel.send(random.choice(RARE_HEWOS))
            else:
                await message.channel.send('HEWO ' * hewos)


async def setup(bot: commands.Bot):
    await bot.add_cog(Hewo(bot))
