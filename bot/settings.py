import json
import os
from pathlib import Path

def create_bot_files_dict(zodiac_signs: [], json_path : Path):
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r') as file:
                bot_files_dict = json.load(file)
                return bot_files_dict
        except Exception as e:
            pass

    bot_files_dict = {sign['ru']: {'path': None, 'id': None} for sign in zodiac_signs}
    with open(json_path, 'w') as file:
        json.dump(bot_files_dict, file, indent=4, ensure_ascii=False)
    return bot_files_dict


zodiac_signs = [
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