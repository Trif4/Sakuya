import asyncio
import os

from dotenv import load_dotenv
load_dotenv()

from sakuya.client import start

asyncio.run(start(os.getenv('DISCORD_TOKEN')))
