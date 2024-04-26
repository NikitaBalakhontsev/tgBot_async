import os

from aiogram import F, Router, Bot
from aiogram.filters import CommandStart, StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery, FSInputFile, ReplyKeyboardRemove

import bot.keyboards as kb
private_router = Router()

class Customer(StatesGroup):
    start = State()
    #gender = State()
    zodiac_sign = State()
    confirm = State()
    payment = State()


ZODIAC_SINGS = [
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

# Проверка, что пользователь подписан на канал по команде старт
@private_router.message(StateFilter(None))
@private_router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot, state: FSMContext):
    channel_id = os.getenv("CHANNEL_ID")
    user_channel_info = await bot.get_chat_member(user_id=message.from_user.id, chat_id=channel_id)

    if user_channel_info.status == 'kicked':
        await message.answer('Ты в бане, свяжись с администраторами группы ...')
    elif user_channel_info.status == 'left':
        #Пригласительная ссылка
        chat = await bot.get_chat(channel_id)
        if hasattr(chat, 'invite_link') and chat.invite_link:
            invite_link = chat.invite_link
        else:
            invite_link = await bot.export_chat_invite_link(channel_id)
        await message.answer(f'Рад, что тебе заинтересовал прогноз, сначала подпишись на канал {invite_link}')
    else:
        await message.answer('Приветственное сообщение ...', reply_markup=kb.get_callback_btns(btns={
            'Получить прогноз': 'predict'
        }))
        await state.set_state(Customer.start)

'''
@private_router.message(Customer.start, (F.text.casefold() == 'узнать прогноз') | (F.text.casefold().contains('прогноз')))
async def display_zodiac_signs(message: Message):
    zodiac_btns = {sign['ru']: sign['en'] for sign in ZODIAC_SINGS}
    await message.answer(text='Выбери знак зодиака', reply_markup=kb.get_callback_btns(btns=zodiac_btns))
'''

@private_router.callback_query(F.data == 'predict')
async def display_zodiac_signs(callback: CallbackQuery):
    zodiac_btns = {sign['ru']: sign['en'] for sign in ZODIAC_SINGS}
    await callback.message.answer(text='Выбери знак зодиака', reply_markup=kb.get_callback_btns(btns=zodiac_btns))

@private_router.callback_query(F.data.in_({'aries', 'taurus', 'gemini', 'cancer', 'leo', 'virgo', 'libra', 'scorpio', 'sagittarius',
                    'capricorn', 'aquarius', 'pisces'}))
async def handle_zodiac_sign(callback: CallbackQuery, state: FSMContext):
    en_zodiac_sign = callback.data
    for sign in ZODIAC_SINGS:
        if sign['en'] == en_zodiac_sign:
            ru_zodiac_sign = sign['ru']

    await state.update_data(zodiac_sign=callback.data)
    await callback.message.edit_text(text=f'Выбран знак зодиака', reply_markup=kb.get_callback_btns(btns={
        ru_zodiac_sign: 'none'
    }))
    await state.set_state(Customer.confirm)
    await display_data(message=callback.message, state=state)


async def display_data(message: Message, state: FSMContext):
    state_data = await state.get_data()
    en_zodiac_sign = state_data['zodiac_sign']
    for sign in ZODIAC_SINGS:
        if sign['en'] == en_zodiac_sign:
            ru_zodiac_sign = sign['ru']

    await message.answer(text=f'Подтвердите данные {ru_zodiac_sign}', reply_markup=kb.get_callback_btns(btns={
        'Подтвердить': 'confirm_btn',
        'Назад': 'back_btn'
    }))

'''
@private_router.message(StateFilter('*'), Command("отмена"))
@private_router.message(StateFilter('*'), F.text.casefold() == "отмена")
async def cancel_handler(message: Message, state: FSMContext) -> None:

    current_state = await state.get_state()
    if current_state is None:
        return

    await state.clear()
    await message.answer("Действия отменены")


#Вернутся на шаг назад (на прошлое состояние)

@private_router.message(StateFilter('*'), Command("назад"))
@private_router.message(StateFilter('*'), F.text.casefold() == "назад")
async def back_step_handler(message: Message, state: FSMContext) -> None:

    current_state = await state.get_state()

    if current_state == Customer.start or current_state == Customer.zodiac_sign:
        await message.answer('Предыдущего шага нет')
        return

    elif current_state == Customer.confirm:
        await state.set_state(Customer.zodiac_sign)
        await display_zodiac_signs(message=message)

    elif current_state == Customer.payment:
        await state.set_state(Customer.confirm)
        await display_data(message=message, state=state)
'''

@private_router.callback_query(F.data == 'back_btn')
async def back_step_handler(callback: CallbackQuery, state: FSMContext) -> None:

    current_state = await state.get_state()

    if current_state == Customer.start or current_state == Customer.zodiac_sign:
        await callback.message.answer('Предыдущего шага нет')
        return

    elif current_state == Customer.confirm:
        await state.set_state(Customer.zodiac_sign)
        await display_zodiac_signs(callback=callback)

    elif current_state == Customer.payment:
        await state.set_state(Customer.confirm)
        await display_data(callback=callback.message, state=state)

payments_router = Router()
'''
@payments_router.message(F.text, F.text.casefold() == 'подтвердить')
async def payment(message: Message, bot: Bot, state: FSMContext):
    await state.set_state(Customer.payment)
    await message.answer(text='Данные подтверждены, переходим к оплате')
    await bot.send_invoice(message.chat.id,
                           'Прогноз',
                           'Ты узнаешь все',
                           'invoice',
                           os.getenv('PAYMENT_TOKEN'),
                           'RUB',
                           [LabeledPrice(label='Прогноз', amount= 200 * 100)]
                           )
'''

@payments_router.callback_query(F.data == 'confirm_btn')
async def payment(callback: CallbackQuery, bot: Bot, state: FSMContext):
    await state.set_state(Customer.payment)
    await callback.message.answer(text='Данные подтверждены, переходим к оплате')
    await bot.send_invoice(callback.message.chat.id,
                           'Прогноз',
                           'Ты узнаешь все',
                           'invoice',
                           os.getenv('PAYMENT_TOKEN'),
                           'RUB',
                           [LabeledPrice(label='Прогноз', amount= 200 * 100)]
                           )

@payments_router.pre_checkout_query(lambda query: True)
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery, bot: Bot):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@payments_router.message(F.successful_payment)
async def successful_payment(message: Message, state: FSMContext):
    for j,k in message.successful_payment:
        print(f"{j} = {k}")
    await state.update_data(payment=message.successful_payment)
    await message.answer(f'Ваш платеж на сумму {message.successful_payment.total_amount // 100} прошел успешно. Ниже прикреплен файл с разбором' )
    await message.answer_document(FSInputFile(path=r'C:\Users\Nikita\pycharmProjects\tg_bot_test\data\test.pdf'))

    print(await state.get_data())
    await state.clear()

