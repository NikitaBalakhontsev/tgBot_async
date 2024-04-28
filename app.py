import asyncio
import logging
import os
import pathlib

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.strategy import FSMStrategy

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from bot.handlers.user_private import user_private_router, payments_router
from bot.handlers.admin_private import admin_router
from bot.handlers.channel import channel_router


bot = Bot(token=os.getenv('BOT_TOKEN'), parse_mode=ParseMode.HTML)

#Дополнительные поля бота, используются в качестве настроек бота из админки.
#Additional bot fields are used as bot settings from the admin panel.
bot.my_admins_list = []
bot.zodiac_signs = [
    {'ru': 'Овен', 'en': 'aries'},
    {'ru': 'Телец', 'en': 'taurus'},
    {'ru': 'Близнецы', 'en': 'gemini'},
    {'ru': 'Рак', 'en': 'cancer'},
    {'ru': 'Лев', 'en': 'leo'},
    {'ru': 'Дева', 'en': 'virgo'},
    {'ru': 'Весы', 'en': 'libra'},
    {'ru': 'Скорпион', 'en': 'scorpio'},
    {'ru': 'Стрелец', 'en': 'sagittarius'},
    {'ru': 'Козерог', 'en': 'capricorn'},
    {'ru': 'Водолей', 'en': 'aquarius'},
    {'ru': 'Рыбы', 'en': 'pisces'},
]
bot.files_dict = {sign['ru']: 'none' for sign in bot.zodiac_signs}
bot.data_path = pathlib.Path('data/')
bot.price = None

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
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Exit by keyboard')
