from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, FSInputFile
from bot.keyboards import zodiac_signs

import bot.keyboards as kb

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer('Приветственное сообщение ...')


@router.message(F.text == 'Узнать прогноз')
async def cmd_start(message: Message):
    await message.answer('Выбери знак зодиака', reply_markup=await kb.get_zodiac_sings())


@router.callback_query()
async def handle_zodiac_sign(callback: CallbackQuery):
    zodiac_signs = ["aries", "taurus", "gemini", "cancer", "leo", "virgo", "libra", "scorpio", "sagittarius",
                    "capricorn", "aquarius", "pisces"]
    if callback.data in zodiac_signs:
        await callback.message.edit_text(text=f'Выбран знак зодиака', reply_markup=await kb.get_zodiac_sings(selected_sign=callback.data, callback='payment'))
    else:
        pass
