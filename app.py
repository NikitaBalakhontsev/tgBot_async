import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.strategy import FSMStrategy

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from bot.handlers.private_user import private_router, payments_router

bot = Bot(token=os.getenv('BOT_TOKEN'), parse_mode=ParseMode.HTML)
dp = Dispatcher()
dp.include_routers(private_router, payments_router)


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Exit by keyboard')
