from discord.ext.commands import Bot

prefixes = (variant(p + ', ') for p in (
        '@Sakuya',
        'Sakuya',
        'Maid robot',
        'Maid bot',
        'Maid',
        'Knife lady',
        'Female Dio'
    ) for variant in (
        lambda p: p,
        lambda p: p.lower(),
        lambda p: p[:-1],
        lambda p: p.lower()[:-1],
        lambda p: p[:-2],
        lambda p: p.lower()[:-2]
    )
)

client = Bot(command_prefix=prefixes, help_command=None)

client.load_extension('sakuya.hi')
