import asyncio
import os

from dotenv import load_dotenv

import bot
import website

load_dotenv()
TOKEN: str = os.getenv('DISCORD_TOKEN')

if __name__ == "__main__":
    asyncio.ensure_future(website.run_website())
    asyncio.ensure_future(bot.start_bot(TOKEN))

    loop = asyncio.get_event_loop()
    loop.run_forever()
