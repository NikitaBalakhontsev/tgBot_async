import asyncio
import logging.config
import os

from aiogram import Dispatcher
from aiogram.enums import ParseMode
from bot.extended_bot import ExtendedBot

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from bot.handlers.user_private import user_private_router, payments_router
from bot.handlers.admin_private import admin_router
from bot.handlers.channel import channel_router
from logging_setup import setup_logging

"""ExtendedBot  наследуется от Aiogram Bot, с добавлением атрибутов file_system, admins_list, price"""
bot = ExtendedBot(os.getenv("BOT_TOKEN"), parse_mode=ParseMode.HTML)

dp = Dispatcher()
dp.include_routers(channel_router,
                   admin_router,
                   payments_router,
                   user_private_router
                   )


async def main():
    await bot.file_system.initial_state()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())



if __name__ == '__main__':
    setup_logging()
    logger = logging.getLogger(__name__)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Exit by keyboard')
