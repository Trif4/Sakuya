import asyncio
import os

import discord
from discord.ext.commands import Bot

base_prefixes = [
    'Sakuya',
    'Maid robot',
    'Maid bot',
    'Maid',
    'Knife lady',
    'Female Dio',
    'Girl Dio'
]

discord_id = os.getenv('DISCORD_ID')
if discord_id:
    base_prefixes.append(f"<@!{os.getenv('DISCORD_ID')}>")
    base_prefixes.append(f"<@{os.getenv('DISCORD_ID')}>")

prefixes = [variant(p) for p in base_prefixes for variant in (
        lambda p: p + ' ',
        lambda p: p + ', ',
        lambda p: p.lower() + ' ',
        lambda p: p.lower() + ', ',
    )
]

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

discord.utils.setup_logging()

bot = Bot(
    command_prefix=prefixes,
    intents=intents,
    help_command=None,
    activity=discord.Activity(type=discord.ActivityType.watching, name='you')
)


async def start(token: str):
    await asyncio.gather(
        bot.load_extension('sakuya.settings'),
        bot.load_extension('sakuya.hi'),
        bot.load_extension('sakuya.hewo'),
        bot.load_extension('sakuya.sentinel'),
        bot.load_extension('sakuya.minecraft'),
        bot.load_extension('sakuya.wordle'),
    )
    await bot.start(token)
