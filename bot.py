import os

from dotenv import load_dotenv

from sakuya.client import bot

load_dotenv()

bot.run(os.getenv('DISCORD_TOKEN'))
