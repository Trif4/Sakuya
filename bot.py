import os

from dotenv import load_dotenv
load_dotenv()

from sakuya.client import bot

bot.run(os.getenv('DISCORD_TOKEN'))
