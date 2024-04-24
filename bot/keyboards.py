from aiogram.types import (InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton)
from aiogram.utils.keyboard import ReplyKeyboardMarkup, InlineKeyboardBuilder

zodiac_signs = [
    {'name': 'Овен', 'callback': 'aries'},
    {'name': 'Телец', 'callback': 'taurus'},
    {'name': 'Близнецы', 'callback': 'gemini'},
    {'name': 'Рак', 'callback': 'cancer'},
    {'name': 'Лев', 'callback': 'leo'},
    {'name': 'Дева', 'callback': 'virgo'},
    {'name': 'Весы', 'callback': 'libra'},
    {'name': 'Скорпион', 'callback': 'scorpio'},
    {'name': 'Стрелец', 'callback': 'sagittarius'},
    {'name': 'Козерог', 'callback': 'capricorn'},
    {'name': 'Водолей', 'callback': 'aquarius'},
    {'name': 'Рыбы', 'callback': 'pisces'},
]

async def get_zodiac_sings(selected_sign=None, callback=None):
    keyboard = InlineKeyboardBuilder()

    if selected_sign:
        selected_sign_info = next((sign for sign in zodiac_signs if sign['callback'] == selected_sign), None)
        if selected_sign_info:
            button_text = selected_sign_info['name']
            callback_data = callback
            keyboard.add(InlineKeyboardButton(text=button_text, callback_data=callback_data))
    else:
        for sign in zodiac_signs:
            button_text = sign['name']
            callback_data = sign['callback']
            keyboard.add(InlineKeyboardButton(text=button_text, callback_data=callback_data))
    return keyboard.adjust(2).as_markup()