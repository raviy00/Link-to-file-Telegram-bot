import asyncio
from telegram import Bot
from dotenv import load_dotenv
import os

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

async def test_bot():
    try:
        bot = Bot(token=BOT_TOKEN)
        me = await bot.get_me()
        print(f"✅ Bot connected successfully!")
        print(f"Bot name: {me.first_name}")
        print(f"Bot username: @{me.username}")
        print(f"Bot ID: {me.id}")
    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_bot())