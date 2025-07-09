import os
from typing import Optional

from aiogram import Bot as AiogramBot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.utils.file_system import FileSystem
from bot.config import data_path, ADMINS


"""
Класс ExtendedBot, расширяющий базовый функционал Aiogram Bot.

Инициализирует объект, передавая токен и необязательные параметры Aiogram Bot
Добавляем file_system, это объект для работы с файловой системой 
Добавляем admins_list, это список администраторов бота, по умолчанию добавляем разработчика
Добавляем price, это цена на товары, по умолчанию 0
"""
class ExtendedBot(AiogramBot):
    def __init__(self, token, *args, **kwargs):
        super().__init__(token, *args, **kwargs)
        self.file_system = FileSystem(bot=self, data_path=data_path)
        self.admins_list = ADMINS
        self.price = 10
        self.scheduler: Optional[AsyncIOScheduler] = None

