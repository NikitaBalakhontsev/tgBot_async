import json
from pathlib import Path
import asyncio


_user_data_lock = asyncio.Lock()
USER_DATA_FILE = Path("user_data.json")

def load_user_data() -> dict:
        if USER_DATA_FILE.exists():
            with USER_DATA_FILE.open("r", encoding="utf-8") as f:
                return json.load(f)
        return {}

async def save_user_data(user_id: int, new_data: dict):
    async with _user_data_lock:
        all_data = load_user_data()
        user_id = str(user_id)

        # Объединяем старые и новые данные
        existing_data = all_data.get(user_id, {})
        existing_data.update(new_data)

        all_data[user_id] = existing_data

        with USER_DATA_FILE.open("w", encoding="utf-8") as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
