import asyncio
import logging
from src.бот.main_bot import bot, dp

logging.basicConfig(level=logging.INFO)

async def main():
    await dp.start_polling(bot, drop_pending_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
