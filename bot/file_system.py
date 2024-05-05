from pathlib import Path
import os
import json
from typing import Optional, Tuple

from aiogram import Bot
import logging

from aiogram.types import FSInputFile

logger = logging.getLogger(__name__)


class FileSystem:
    def __init__(
            self,
            bot: Bot,
            data_path: Path,
            json_path: Path = None
    ) -> None:

        self.bot = bot
        self._set_data_path(data_path)
        self._set_json_path(json_path)
        self._set_default_files()
        logger.info('Init file system')

    def _set_data_path(self, data_path: Path) -> None:
        if os.path.isdir(data_path):
            self.data_path = data_path
        else:
            raise ValueError("param: 'data_path' does not exist or is not a directory")

    def _set_json_path(self, json_path: Path) -> None:
        if (json_path is None) or (json_path.is_file() is False):
            self.json_path = Path(self.data_path, 'files.json')
        else:
            self.json_path = json_path

    def _set_default_files(self) -> None:
        self.files = {sign['ru']: {
            'file_id': None,
            'path': None
        } for sign in self.bot.zodiac_signs}

    async def initial_state(self) -> None:
        """
        Устанавливает начальное состояние класса.
        Добавляет все валидные файлы
        Проверяет JSON, файлы сервера
        """
        await self.load_json()
        self.save_to_json()

        await self.load_local()
        self.save_to_json()

        print(self.get_paths())

    def json_file_exists(self) -> bool:
        """Проверка существования JSON файла."""
        return self.json_path.exists()

    async def load_json(self) -> None:
        """Загрузка данных из JSON файла."""
        try:
            if self.json_path.exists():
                with open(self.json_path, 'r', encoding='utf-8') as file:
                    json_data = json.load(file)
        except Exception as e:
            print("Ошибка про загрузке JSON", e)
        await self.validate_dict(data=json_data)

    async def load_local(self) -> None:
        """Загрузка данных из data/."""
        data_path = self.data_path
        zodiac_signs = [data['ru'] for data in self.bot.zodiac_signs]
        for zodiac_sign in zodiac_signs:
            if self.files[zodiac_sign]['path'] is not None:
                print(f"Локально найден знак зодиака {zodiac_sign}, повтор")
                continue

            path = Path(f'{data_path}/{zodiac_sign}.pdf')
            if self.validate_path(path):
                file_id = await self.get_new_file_id(path=path)
                self.files[zodiac_sign] = {'file_id': file_id, 'path': str(path)}
                print(f"Локально найден знак зодиака {zodiac_sign}, path: {path}, id: {file_id}")

    def custom_json_serializer(obj):
        if obj is None:
            return 'null'
        return obj

    def save_to_json(self) -> None:
        """Сохранение данных в JSON файл."""
        with open(self.json_path, 'w', encoding='utf-8') as file:
            json.dump(self.files, file, ensure_ascii=False, default=self.custom_json_serializer)

    async def validate_dict(self, data: dict) -> None:
        """Проверка данных в файле."""
        for sign, data in data.items():
            file_id = data.get('file_id') if data.get('file_id') else None
            path = Path(data['path']) if data.get('path') else None
            if (file_id is None) and (path is None):
                print(f"[SKIP] Validate. Sign: {sign}, Path: {path}, Id: {file_id}")
                continue

            result, file_id, path = await self.validate(sign=sign, file_id=file_id, path=path)
            self.files[sign]['file_id'] = file_id
            self.files[sign]['path'] = str(path)

    async def validate(self,
                       sign: str,
                       file_id: Optional[str] = None,
                       path: Optional[Path] = None
                       ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
       :param sign: Zodiac_sign, key for files dict
       :param file_id: Telegram id for file
       :param path: Path to local file
       :return: turple [result, file_id, path]
        """
        data_path = self.data_path

        print(f" Validate. Sign: {sign}, Path: {path}, Id: {file_id}")
        if self.validate_path(path) is False:
            print(f"Некорректный Path для знака зодиака {sign}, Path: {path}")
            path = self.get_new_path(data_path=data_path, sign=sign)

        if await self.validate_file_id(file_id) is False:
            print(f"Некорректный Id для знака зодиака {sign}, Id: {file_id}")
            if path:
                file_id = await self.get_new_file_id(path=path)
                print(f"Новый id для знака зодиака {sign}, Id: {file_id}")

        if (path is None) and file_id:
            path = await self.get_new_path_by_file_id(file_id=file_id, sign=sign)

        return [bool(path), file_id, path]

    def validate_path(self, path: Path) -> bool:
        """Проверка существования файла по пути."""
        if path:
            return os.path.exists(path)
        return False

    async def validate_file_id(self, file_id):
        """Проверка корректности file_id."""
        if not isinstance(file_id, str):
            return False
        try:
            file = await self.bot.get_file(file_id=file_id)
            if file is None:
                return False
        except Exception as e:
            logger.info(f"Ошибка при получении файла с сервера Telegram: {e}")
            return False

        return True

    async def get_new_file_id(self, path: Path) -> Optional[str]:
        """Получает новый file_id для локального файла."""
        """Отправляет файлы в чат DEVELOPER_ID"""
        try:
            message = await self.bot.send_document(chat_id=os.getenv('DEVELOPER_ID'),
                                                   document=FSInputFile(path),
                                                   caption=f"Получение нового id для Path: {path}")
            return message.document.file_id

        except Exception as e:
            print(f"Ошибка при загрузке файла: {e}")
            return None

    async def get_new_path_by_file_id(self, file_id: str, sign: str) -> Optional[Path]:
        """Получает новый Path для удаленного файла"""
        try:
            file = await self.bot.get_file(file_id)
            file_path = file.file_path

            filename = f'{sign}.pdf'
            destination = Path(self.data_path, filename)
            await self.bot.download_file(file_path=file_path, destination=destination)
            return destination

        except Exception as e:
            print(f"Ошибка при загрузке файла: {e}")
            return None

    def get_new_path(self, data_path: Path, sign: str) -> Optional[Path]:
        """Получает новый Path для локального файла"""
        path = Path(data_path, f"{sign}.pdf")
        if self.validate_path(path) is True:
            return path
        return None

    def display_files(self):
        print(self.files)

    def get_paths(self) -> [str]:
        return [data['path'] for data in self.files.values() if data['path'] is not None]
