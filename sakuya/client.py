from discord.ext.commands import Bot

prefixes = [variant(p) for p in (
        '<@!678333318202261548>',  # hardcoded bot mention
        'Sakuya',
        'Maid robot',
        'Maid bot',
        'Maid',
        'Knife lady',
        'Female Dio',
        'Girl Dio'
    ) for variant in (
        lambda p: p + ' ',
        lambda p: p + ', ',
        lambda p: p.lower() + ' ',
        lambda p: p.lower() + ', ',
    )
]

bot = Bot(command_prefix=prefixes, help_command=None)

bot.load_extension('sakuya.settings')
bot.load_extension('sakuya.hi')
bot.load_extension('sakuya.sentinel')
