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

async def save_user_data(user_id: int, data: dict):
    async with _user_data_lock:
        all_data = load_user_data()
        all_data[str(user_id)] = data
        with USER_DATA_FILE.open("w", encoding="utf-8") as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
