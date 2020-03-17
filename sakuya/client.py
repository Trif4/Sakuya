import os

from discord import Activity, ActivityType
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

bot = Bot(command_prefix=prefixes, help_command=None, activity=Activity(type=ActivityType.watching, name='you'))

bot.load_extension('sakuya.settings')
bot.load_extension('sakuya.hi')
bot.load_extension('sakuya.sentinel')
bot.load_extension('sakuya.minecraft')
