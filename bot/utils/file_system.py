# import os
# import json
# from datetime import datetime
#
# from aiogram import Bot
# import logging
#
# from typing import Optional, Tuple, Union
# from pathlib import Path
# from aiogram.types import FSInputFile
#
# from bot.config import ZODIAC_SIGNS
#
# logger = logging.getLogger(__name__)
#
#
#
# class FileSystem:
#     def __init__(self, bot: Bot, data_path: Path) -> None:
#         self.bot = bot
#         self._set_data_path(data_path)
#         self.json_path = Path("file_system.json")
#         self._set_default_files()
#         logger.info("Init file system")
#
#     def _set_data_path(self, data_path: Path) -> None:
#         if not os.path.isdir(data_path):
#             os.makedirs(data_path)
#         self.data_path = data_path
#
#     def _set_default_files(self) -> None:
#         self.files = {
#             sign: {
#                 "general": {"file_id": None, "path": None, "upload_date": None},
#                 "detailed": {"file_id": None, "path": None, "upload_date": None}
#             } for sign in ZODIAC_SIGNS
#         }
#
#     async def initial_state(self) -> None:
#         await self.load_json()
#         self.save_to_json()
#         await self.load_local()
#         self.save_to_json()
#         logger.info(self.get_file_paths())
#
#     async def load_json(self) -> None:
#         try:
#             if self.json_path.exists():
#                 with open(self.json_path, 'r', encoding='utf-8') as file:
#                     json_data = json.load(file)
#                 await self._validate_dict(json_data)
#         except Exception as e:
#             logger.error("Ошибка при загрузке JSON", exc_info=e)
#
#     async def load_local(self) -> None:
#         for sign in ZODIAC_SIGNS:
#             for kind in ["general", "detailed"]:
#                 if self.files[sign][kind]['path']:
#                     continue
#                 path = Path(f'{self.data_path}/{sign}_{kind}.pdf')
#                 if self.validate_path(path):
#                     file_id = await self.get_new_file_id(path)
#                     self.files[sign][kind] = {
#                         'file_id': file_id,
#                         'path': str(path),
#                         'upload_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#                     }
#
#     def save_to_json(self) -> None:
#         with open(self.json_path, 'w', encoding='utf-8') as file:
#             json.dump(self.files, file, ensure_ascii=False, indent=2)
#
#     async def _validate_dict(self, data: dict) -> None:
#         for sign, kinds in data.items():
#             for kind in ["general", "detailed"]:
#                 entry = kinds.get(kind, {})
#                 file_id = entry.get('file_id')
#                 path = Path(entry.get('path')) if entry.get('path') else None
#                 upload_date = entry.get('upload_date')
#                 if not file_id and not path:
#                     continue
#                 file_id, path = await self.validate(sign, kind, file_id, path)
#                 self.files[sign][kind]['file_id'] = file_id
#                 self.files[sign][kind]['path'] = str(path) if path else None
#                 self.files[sign][kind]['upload_date'] = upload_date or datetime.now().date().isoformat()
#
#     async def validate(self, sign: str, kind: str, file_id: Optional[str], path: Optional[Path]) -> Tuple[Optional[str], Optional[str]]:
#         if not self.validate_path(path):
#             path = self.get_new_path(sign, kind)
#         if not await self.validate_file_id(file_id):
#             if path:
#                 file_id = await self.get_new_file_id(path)
#         if not path and file_id:
#             path = await self._get_new_path_by_file_id(file_id, sign, kind)
#         return file_id, str(path) if path else None
#
#     def validate_path(self, path: Optional[Path]) -> bool:
#         return path and os.path.exists(path)
#
#     async def validate_file_id(self, file_id: Optional[str]) -> bool:
#         if not isinstance(file_id, str):
#             return False
#         try:
#             file = await self.bot.get_file(file_id)
#             return bool(file)
#         except Exception as e:
#             logger.error(f"Ошибка при валидации file_id: {e}")
#             return False
#
#     async def get_new_file_id(self, path: Path) -> Optional[str]:
#         try:
#             message = await self.bot.send_document(
#                 chat_id=os.getenv('DEVELOPER_ID'),
#                 document=FSInputFile(path),
#                 caption=f"Получение нового file_id для {path.name}"
#             )
#             return message.document.file_id
#         except Exception as e:
#             logger.error(f"Ошибка при отправке документа: {e}")
#             return None
#
#     async def _get_new_path_by_file_id(self, file_id: str, sign: str, kind: str) -> Optional[Path]:
#         try:
#             file = await self.bot.get_file(file_id)
#             filename = f"{sign}_{kind}.pdf"
#             destination = Path(self.data_path, filename)
#             await self.bot.download_file(file.file_path, destination)
#             return destination
#         except Exception as e:
#             logger.error(f"Ошибка при скачивании файла: {e}")
#             return None
#
#     def get_new_path(self, sign: str, kind: str) -> Optional[Path]:
#         path = Path(self.data_path, f"{sign}_{kind}.pdf")
#         return path if self.validate_path(path) else None
#
#     def get_file(self, sign: str, kind: str = "general") -> Union[FSInputFile, str, None]:
#         file_id = self.get_file_id(sign, kind)
#         if file_id:
#             return file_id
#         path = self.get_path(sign, kind)
#         return FSInputFile(path) if path else None
#
#     def get_file_id(self, sign: str, kind: str = "general") -> Optional[str]:
#         return self.files.get(sign, {}).get(kind, {}).get("file_id")
#
#     def get_path(self, sign: str, kind: str = "general") -> Optional[str]:
#         return self.files.get(sign, {}).get(kind, {}).get("path")
#
#     def get_upload_date(self, sign: str, kind: str = "general") -> Optional[str]:
#         return self.files.get(sign, {}).get(kind, {}).get("upload_date")
#
#     async def add_file(self, sign: str, file_id: str, kind: str = "general") -> None:
#         filename = f"{sign}_{kind}.pdf"
#         destination = Path(self.data_path, filename)
#         try:
#             await self.bot.download(file=file_id, destination=destination)
#         except Exception as e:
#             raise ValueError(f"Ошибка при скачивании файла: {e}")
#
#         if sign not in self.files:
#             self.files[sign] = {}
#
#         self.files[sign][kind] = {
#             "file_id": file_id,
#             "path": str(destination),
#             "upload_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")        }
#         self.save_to_json()
#
#     def get_file_paths(self) -> list[str]:
#         return [data[kind]['path'] for data in self.files.values() for kind in ['general', 'detailed'] if data[kind]['path']]
#
#     def display_files(self):
#         for sign, kinds in self.files.items():
#             for kind, info in kinds.items():
#                 print(f"{sign} ({kind}): {info}")
#

import os
import json
from datetime import datetime

from aiogram import Bot
import logging

from typing import Optional, Tuple, Union
from pathlib import Path
from aiogram.types import FSInputFile

from bot.config import ZODIAC_SIGNS

logger = logging.getLogger(__name__)


class FileSystem:
    def __init__(self, bot: Bot, data_path: Path) -> None:
        self.bot = bot
        self._set_data_path(data_path)
        self.json_path = Path("file_system.json")
        self._set_default_files()
        logger.info("Init file system")

    def _set_data_path(self, data_path: Path) -> None:
        if not os.path.isdir(data_path):
            os.makedirs(data_path)
        self.data_path = data_path

    def _set_default_files(self) -> None:
        self.files = {
            sign: {
                "detailed": {"file_id": None, "path": None, "upload_date": None}
            } for sign in ZODIAC_SIGNS
        }
        self.files["general_queue"] = []

    async def initial_state(self) -> None:
        await self.load_json()
        self.save_to_json()
        await self.load_local()
        self.save_to_json()
        logger.info(self.get_file_paths())

    async def load_json(self) -> None:
        try:
            if self.json_path.exists():
                with open(self.json_path, 'r', encoding='utf-8') as file:
                    json_data = json.load(file)
                await self._validate_dict(json_data)
        except Exception as e:
            logger.error("Ошибка при загрузке JSON", exc_info=e)

    async def load_local(self) -> None:
        for sign in ZODIAC_SIGNS:
            if self.files[sign]['detailed']['path']:
                continue
            path = Path(f'{self.data_path}/{sign}_detailed.pdf')
            if self.validate_path(path):
                file_id = await self.get_new_file_id(path)
                self.files[sign]['detailed'] = {
                    'file_id': file_id,
                    'path': str(path),
                    'upload_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }

    def save_to_json(self) -> None:
        with open(self.json_path, 'w', encoding='utf-8') as file:
            json.dump(self.files, file, ensure_ascii=False, indent=2)

    async def _validate_dict(self, data: dict) -> None:
        for sign, kinds in data.items():
            if sign == "general_queue":
                self.files["general_queue"] = kinds if isinstance(kinds, list) else []
                continue
            entry = kinds.get("detailed", {})
            file_id = entry.get('file_id')
            path = Path(entry.get('path')) if entry.get('path') else None
            upload_date = entry.get('upload_date')
            if not file_id and not path:
                continue
            file_id, path = await self.validate(sign, "detailed", file_id, path)
            self.files[sign]["detailed"] = {
                'file_id': file_id,
                'path': str(path) if path else None,
                'upload_date': upload_date or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

    async def validate(self, sign: str, kind: str, file_id: Optional[str], path: Optional[Path]) -> Tuple[Optional[str], Optional[str]]:
        if not self.validate_path(path):
            path = self.get_new_path(sign, kind)
        if not await self.validate_file_id(file_id):
            if path:
                file_id = await self.get_new_file_id(path)
        if not path and file_id:
            path = await self._get_new_path_by_file_id(file_id, sign, kind)
        return file_id, str(path) if path else None

    def validate_path(self, path: Optional[Path]) -> bool:
        return path and os.path.exists(path)

    async def validate_file_id(self, file_id: Optional[str]) -> bool:
        if not isinstance(file_id, str):
            return False
        try:
            file = await self.bot.get_file(file_id)
            return bool(file)
        except Exception as e:
            logger.error(f"Ошибка при валидации file_id: {e}")
            return False

    async def get_new_file_id(self, path: Path) -> Optional[str]:
        try:
            message = await self.bot.send_document(
                chat_id=os.getenv('DEVELOPER_ID'),
                document=FSInputFile(path),
                caption=f"Получение нового file_id для {path.name}"
            )
            return message.document.file_id
        except Exception as e:
            logger.error(f"Ошибка при отправке документа: {e}")
            return None

    async def _get_new_path_by_file_id(self, file_id: str, sign: str, kind: str) -> Optional[Path]:
        try:
            file = await self.bot.get_file(file_id)
            filename = f"{sign}_{kind}.pdf"
            destination = Path(self.data_path, filename)
            await self.bot.download_file(file.file_path, destination)
            return destination
        except Exception as e:
            logger.error(f"Ошибка при скачивании файла: {e}")
            return None

    def get_new_path(self, sign: str, kind: str) -> Optional[Path]:
        path = Path(self.data_path, f"{sign}_{kind}.pdf")
        return path if self.validate_path(path) else None

    def get_file(self, sign: str, kind: str = "general") -> Union[FSInputFile, str, None]:
        if sign == "general_queue":
            if self.files["general_queue"]:
                entry = self.files["general_queue"][0]
                return entry.get("file_id") or FSInputFile(entry.get("path")) if entry.get("path") else None
            return None
        file_id = self.get_file_id(sign, kind)
        if file_id:
            return file_id
        path = self.get_path(sign, kind)
        return FSInputFile(path) if path else None

    def get_file_id(self, sign: str, kind: str = "general") -> Optional[str]:
        if sign == "general_queue":
            return self.files["general_queue"][0].get("file_id") if self.files["general_queue"] else None
        return self.files.get(sign, {}).get(kind, {}).get("file_id")

    def get_path(self, sign: str, kind: str = "general") -> Optional[str]:
        if sign == "general_queue":
            return self.files["general_queue"][0].get("path") if self.files["general_queue"] else None
        return self.files.get(sign, {}).get(kind, {}).get("path")

    def get_upload_date(self, sign: str, kind: str = "general") -> Optional[str]:
        if sign == "general_queue":
            return self.files["general_queue"][0].get("upload_date") if self.files["general_queue"] else None
        return self.files.get(sign, {}).get(kind, {}).get("upload_date")

    async def add_file(self, sign: str, file_id: str, kind: str = "general") -> Union[None, str]:
        filename = f"{sign}_{kind}.pdf"
        destination = Path(self.data_path, filename)

        try:
            await self.bot.download(file=file_id, destination=destination)
        except Exception as e:
            return f"Ошибка при скачивании файла: {e}"

        if sign == "general_queue":
            self.files["general_queue"].append({
                "file_id": file_id,
                "path": str(destination),
                "upload_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            if len(self.files["general_queue"]) > 7:
                self.files["general_queue"] = self.files["general_queue"][-7:]
        else:
            if sign not in self.files:
                self.files[sign] = {}
            self.files[sign][kind] = {
                "file_id": file_id,
                "path": str(destination),
                "upload_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

        self.save_to_json()
        return None


    async def replace_general_file(self, index: int, file_id: str) -> Optional[str]:
        try:
            if not (0 <= index < len(self.files["general_queue"])):
                return f"Элемент с индексом {index} отсутствует в очереди."

            filename = f"general_queue_{index+1}.pdf"
            destination = Path(self.data_path, filename)

            await self.bot.download(file=file_id, destination=destination)

            self.files["general_queue"][index] = {
                "file_id": file_id,
                "path": str(destination),
                "upload_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            self.save_to_json()
            return None
        except Exception as e:
            return f"Ошибка при замене файла: {e}"

    def shift_general_queue(self) -> None:
        """Удаляет первый файл из очереди и сдвигает остальные на одну позицию."""
        if self.files["general_queue"]:
            removed = self.files["general_queue"].pop(0)
            logger.info(f"Удалён файл из очереди: {removed.get('path')}")
            self.save_to_json()

    def get_file_paths(self) -> list[str]:
        paths = []
        for sign, data in self.files.items():
            if sign == "general_queue":
                for entry in data:
                    if entry["path"]:
                        paths.append(entry["path"])
            else:
                if data.get("detailed", {}).get("path"):
                    paths.append(data["detailed"]["path"])
        return paths

    def display_files(self):
        for sign, kinds in self.files.items():
            if sign == "general_queue":
                for i, entry in enumerate(kinds):
                    print(f"Очередь {i+1}: {entry}")
            else:
                for kind, info in kinds.items():
                    print(f"{sign} ({kind}): {info}")