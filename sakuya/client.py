from discord.ext.commands import Bot

prefixes = [variant(p) for p in (
        '<@!678333318202261548>',  # hardcoded bot mention
        'Sakuya',
        'Maid robot',
        'Maid bot',
        'Maid',
        'Knife lady',
        'Female Dio'
    ) for variant in (
        lambda p: p + ' ',
        lambda p: p + ', ',
        lambda p: p.lower() + ' ',
        lambda p: p.lower() + ', ',
    )
]

client = Bot(command_prefix=prefixes, help_command=None)

client.load_extension('sakuya.hi')
