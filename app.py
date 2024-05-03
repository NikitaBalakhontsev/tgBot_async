import asyncio
import logging.config
import os
from pathlib import Path
import json

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.strategy import FSMStrategy

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

from bot.handlers.user_private import user_private_router, payments_router
from bot.handlers.admin_private import admin_router
from bot.handlers.channel import channel_router
from logging_setup import setup_logging
from bot.settings import zodiac_signs, create_bot_files_dict

bot = Bot(token=os.getenv('BOT_TOKEN'), parse_mode=ParseMode.HTML)

# Дополнительные поля бота, используются в качестве настроек бота из админки.
# Additional bot fields are used as bot settings from the admin panel.

# bot.my admin_list хранит id администраторов канала. Заполняется в channel.py
bot.my_admins_list = []
# bot.zodiac_signs хранит знаки зодиака, ru используется для пользователя 'en' для callback
bot.zodiac_signs = zodiac_signs
# bot.data_path хранит путь к директории data, в которой хранятся файлы .pdf
bot.data_path = Path('data')
# bot. files_dict хранит знак зодиака и путь к связанному .pdf файлу. Заполняется в admin.private.py
bot.files_dict = create_bot_files_dict(zodiac_signs=zodiac_signs, json_path=Path(bot.data_path, 'files.json'))

# bot.price цена на услугу. Заполняется в admin.private.py
bot.price = 0

dp = Dispatcher()
dp.include_routers(channel_router,
                   admin_router,
                   payments_router,
                   user_private_router
                   )


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == '__main__':
    setup_logging()
    logger = logging.getLogger(__name__)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Exit by keyboard')
