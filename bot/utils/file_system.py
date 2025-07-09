import os
import json
from datetime import datetime
from typing import Optional, Tuple, Union
from pathlib import Path
import logging

from aiogram import Bot
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
                "detailed": {"image_id": None, "path": None, "text": "", "upload_date": None}
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
            for ext in ["jpg", "jpeg", "png"]:
                path = Path(f'{self.data_path}/{sign}_detailed.{ext}')
                if self.validate_path(path):
                    image_id = await self.get_new_image_id(path)
                    self.files[sign]['detailed'] = {
                        'image_id': image_id,
                        'path': str(path),
                        'text': '',
                        'upload_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    break

    def save_to_json(self) -> None:
        with open(self.json_path, 'w', encoding='utf-8') as file:
            json.dump(self.files, file, ensure_ascii=False, indent=2)

    async def _validate_dict(self, data: dict) -> None:
        for sign, kinds in data.items():
            if sign == "general_queue":
                self.files["general_queue"] = kinds if isinstance(kinds, list) else []
                continue
            entry = kinds.get("detailed", {})
            image_id = entry.get('image_id')
            path = Path(entry.get('path')) if entry.get('path') else None
            upload_date = entry.get('upload_date')
            text = entry.get('text', '')

            if not image_id and not path:
                continue
            image_id, path = await self.validate(sign, "detailed", image_id, path)
            self.files[sign]["detailed"] = {
                'image_id': image_id,
                'path': str(path) if path else None,
                'text': text,
                'upload_date': upload_date or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

    async def validate(self, sign: str, kind: str, image_id: Optional[str], path: Optional[Path]) -> Tuple[Optional[str], Optional[str]]:
        if not self.validate_path(path):
            path = self.get_new_path(sign, kind)
        if not await self.validate_file_id(image_id):
            if path:
                image_id = await self.get_new_image_id(path)
        if not path and image_id:
            path = await self._get_new_path_by_file_id(image_id, sign, kind)
        return image_id, str(path) if path else None

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

    async def get_new_image_id(self, path: Path) -> Optional[str]:
        try:
            message = await self.bot.send_photo(
                chat_id=os.getenv('DEVELOPER_ID'),
                photo=FSInputFile(path),
                caption=f"Получение нового image_id для {path.name}"
            )
            return message.photo[-1].file_id
        except Exception as e:
            logger.error(f"Ошибка при отправке изображения: {e}")
            return None

    async def _get_new_path_by_file_id(self, file_id: str, sign: str, kind: str) -> Optional[Path]:
        try:
            file = await self.bot.get_file(file_id)
            filename = f"{sign}_{kind}.jpg"
            destination = Path(self.data_path, filename)
            await self.bot.download_file(file.file_path, destination)
            return destination
        except Exception as e:
            logger.error(f"Ошибка при скачивании файла: {e}")
            return None

    def get_new_path(self, sign: str, kind: str) -> Optional[Path]:
        for ext in ["jpg", "jpeg", "png"]:
            path = Path(self.data_path, f"{sign}_{kind}.{ext}")
            if self.validate_path(path):
                return path
        return None

    def get_image(self, sign: str, kind: str = "detailed") -> Union[Tuple[Union[str, FSInputFile], Optional[str]], None]:
        if sign == "general_queue":
            if self.files["general_queue"]:
                entry = self.files["general_queue"][0]
                image = entry.get("image_id") or (FSInputFile(entry["path"]) if entry.get("path") else None)
                return (image, entry.get("text", ""))
            return None
        entry = self.files.get(sign, {}).get(kind, {})
        image = entry.get("image_id") or (FSInputFile(entry["path"]) if entry.get("path") else None)
        return (image, entry.get("text", "")) if image else None

    def get_image_id(self, sign: str, kind: str = "detailed") -> Optional[str]:
        if sign == "general_queue":
            return self.files["general_queue"][0].get("image_id") if self.files["general_queue"] else None
        return self.files.get(sign, {}).get(kind, {}).get("image_id")

    def get_path(self, sign: str, kind: str = "detailed") -> Optional[str]:
        if sign == "general_queue":
            return self.files["general_queue"][0].get("path") if self.files["general_queue"] else None
        return self.files.get(sign, {}).get(kind, {}).get("path")

    def get_upload_date(self, sign: str, kind: str = "detailed") -> Optional[str]:
        if sign == "general_queue":
            return self.files["general_queue"][0].get("upload_date") if self.files["general_queue"] else None
        return self.files.get(sign, {}).get(kind, {}).get("upload_date")

    async def add_file(self, sign: str, image_id: str, kind: str = "detailed", text: Optional[str] = None) -> Union[None, str]:
        if sign == "general_queue":
            # Определяем порядковый номер (от 1 до 7)
            kind = str(len(self.files["general_queue"]) + 1)
            filename = f"{sign}_{kind}.jpg"
        else:
            filename = f"{sign}_{kind}.jpg"

        destination = Path(self.data_path, filename)

        try:
            await self.bot.download(file=image_id, destination=destination)
        except Exception as e:
            return f"Ошибка при скачивании изображения: {e}"

        entry = {
            "image_id": image_id,
            "path": str(destination),
            "text": text or "",
            "upload_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        if sign == "general_queue":
            self.files["general_queue"].append(entry)
            if len(self.files["general_queue"]) > 7:
                self.files["general_queue"] = self.files["general_queue"][-7:]
        else:
            if sign not in self.files:
                self.files[sign] = {}
            self.files[sign][kind] = entry

        self.save_to_json()
        return None

    async def replace_general_file(self, index: int, image_id: str, text: Optional[str] = None) -> Optional[str]:
        try:
            if not (0 <= index < len(self.files["general_queue"])):
                return f"Элемент с индексом {index} отсутствует в очереди."

            filename = f"general_queue_{index+1}.jpg"
            destination = Path(self.data_path, filename)

            await self.bot.download(file=image_id, destination=destination)

            self.files["general_queue"][index] = {
                "image_id": image_id,
                "path": str(destination),
                "text": text or "",
                "upload_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            self.save_to_json()
            return None
        except Exception as e:
            return f"Ошибка при замене изображения: {e}"

    def shift_general_queue(self) -> None:
        if not self.files["general_queue"]:
            return

        # Удаляем первый файл из очереди
        removed_entry = self.files["general_queue"].pop(0)
        removed_path = removed_entry.get("path")
        if removed_path:
            try:
                Path(removed_path).unlink(missing_ok=True)
                logger.info(f"Удалён файл из очереди: {removed_path}")
            except Exception as e:
                logger.warning(f"Не удалось удалить файл {removed_path}: {e}")

        # Переписываем пути без переименования (сохраняем старые)
        new_paths = []
        for idx, entry in enumerate(self.files["general_queue"], start=1):
            new_filename = f"general_queue_{idx}.jpg"
            new_path = str(Path(self.data_path) / new_filename)
            new_paths.append((entry, new_path))

        # Переименовываем только после подготовки новых путей
        for (entry, new_path) in new_paths:
            old_path = entry.get("path")
            if not old_path:
                continue

            try:
                new_path_obj = Path(new_path)
                if new_path_obj.exists():
                    new_path_obj.unlink()  # удаляем существующий новый, если вдруг остался

                Path(old_path).rename(new_path)
                entry["path"] = new_path
            except Exception as e:
                logger.warning(f"Не удалось переименовать файл {old_path} в {new_path}: {e}")

        self.save_to_json()

    def get_file_paths(self) -> list[str]:
        paths = []
        for sign, data in self.files.items():
            if sign == "general_queue":
                for entry in data:
                    if entry.get("path"):
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
