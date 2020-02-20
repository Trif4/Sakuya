import os

from dotenv import load_dotenv

from .client import client

load_dotenv()

client.run(os.getenv('DISCORD_TOKEN'))
