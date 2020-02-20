import os

from dotenv import load_dotenv

from sakuya.client import client

load_dotenv()

client.run(os.getenv('DISCORD_TOKEN'))
