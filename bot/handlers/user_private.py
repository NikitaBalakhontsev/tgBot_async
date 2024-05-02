import json
import os
import pathlib
import logging

from datetime import datetime as datetime

from aiogram import F, Router, Bot
from aiogram.filters import CommandStart, StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery, FSInputFile, ReplyKeyboardRemove

import bot.keyboards as kb
from bot.filters import ChatTypeFilter, IsAdmin

user_private_router = Router()
payment_loger = logging.getLogger('payment')


# Отключить админам базовый сценарий бота
# user_private_router.message.filter(ChatTypeFilter(["private"]), ~IsAdmin())

class Customer(StatesGroup):
    start = State()
    # gender = State()
    zodiac_sign = State()
    confirm = State()

    ru_zodiac_sign = ''
    en_zodiac_sign = ''


# Проверка, что пользователь подписан на канал по команде старт
@user_private_router.message(StateFilter(None))
@user_private_router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot, state: FSMContext):
    channel_id = os.getenv("CHANNEL_ID")
    user_channel_info = await bot.get_chat_member(user_id=message.from_user.id, chat_id=channel_id)

    if user_channel_info.status == 'kicked':
        await message.answer('Вы в бане, свяжись с администраторами группы ...')

    elif user_channel_info.status == 'left':
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
        await state.clear()
        await state.set_state(Customer.start)


'''
@private_router.message(Customer.start, (F.text.casefold() == 'узнать прогноз') | (F.text.casefold().contains('прогноз')))
async def display_zodiac_signs(message: Message, bot: Bot):
    zodiac_btns = {sign['ru']: sign['en'] for sign in bot.zodiac_signs}
    await message.answer(text='Выбери знак зодиака', reply_markup=kb.get_callback_btns(btns=zodiac_btns))
'''


@user_private_router.callback_query(StateFilter(Customer.start), F.data == 'predict')
@user_private_router.callback_query(StateFilter(Customer.confirm), F.data == 'back_btn')
async def display_zodiac_signs(callback: CallbackQuery, bot: Bot, state: FSMContext):
    zodiac_btns = {sign['ru']: sign['en'] for sign in bot.zodiac_signs}

    await state.set_state(Customer.zodiac_sign)
    text = 'Выбери знак зодиака'
    reply_markup = kb.get_callback_btns(btns=zodiac_btns)
    if callback.data == 'back_btn':
        await callback.message.edit_text(text=text, reply_markup=reply_markup)
    else:
        await callback.message.answer(text=text, reply_markup=reply_markup)


@user_private_router.callback_query(StateFilter(Customer.zodiac_sign), F.data.in_({
    'aries', 'taurus', 'gemini', 'cancer', 'leo', 'virgo', 'libra', 'scorpio', 'sagittarius',
    'capricorn', 'aquarius', 'pisces'}))
async def handle_zodiac_sign(callback: CallbackQuery, state: FSMContext, bot: Bot):
    en_zodiac_sign = callback.data
    ru_zodiac_sign = None
    for sign in bot.zodiac_signs:
        if sign['en'] == en_zodiac_sign:
            ru_zodiac_sign = sign['ru']

    await state.clear()
    await state.set_state(Customer.confirm)
    await state.update_data(ru_zodiac_sign=ru_zodiac_sign, en_zodiac_sign=en_zodiac_sign)
    await callback.message.edit_text(text=f'Прогноз почти у вас, остался последний шаг \n'
                                          f'Подтвердите данные \n'
                                          f'Знак зодиака <b>[{ru_zodiac_sign}]</b> \n'
                                          f'Сумма платежа <b>[{bot.price // 100}]</b>',
                                     reply_markup=kb.get_callback_btns(btns={

                                         'Подтвердить': 'confirm_btn',
                                         'Назад': 'back_btn'
                                     }))



'''
async def display_data(message: Message, state: FSMContext, bot: Bot):
    state_data = await state.get_data()
    ru_zodiac_sign = state_data['ru_zodiac_sign']
    await message.answer(text=f'Прогноз почти у вас, остался последний шаг \n'
                              f'Подтвердите данные \n'
                              f'Знак зодиака <b>[{ru_zodiac_sign}]</b> \n'
                              f'Сумма платежа <b>[{bot.price // 100}]</b>',
                         reply_markup=kb.get_callback_btns(btns={

                             'Подтвердить': 'confirm_btn',
                             'Назад': 'back_btn'
                         }))
'''

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

'''
@user_private_router.callback_query(F.data == 'back_btn')
async def back_step_handler(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    current_state = await state.get_state()

    if current_state == Customer.start or current_state == Customer.zodiac_sign:
        await callback.message.answer('Предыдущего шага нет')
        return

    elif current_state == Customer.confirm:
        await state.set_state(Customer.zodiac_sign)
        await display_zodiac_signs(callback=callback, bot=bot)

    elif current_state == Customer.payment:
        await state.set_state(Customer.confirm)
        await display_data(callback=callback.message, state=state, bot=bot)
'''

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


@payments_router.callback_query(StateFilter(Customer.confirm), F.data == 'confirm_btn')
async def order(callback: CallbackQuery, bot: Bot, state: FSMContext):
    state_data = await state.get_data()
    ru_zodiac_sign = state_data['ru_zodiac_sign']

    await bot.send_invoice(callback.message.chat.id,
                           title='Прогноз',
                           description=f'Ты узнаешь все о {ru_zodiac_sign}',
                           payload='invoice',
                           provider_token=os.getenv('LIVE_PAYMENT_TOKEN'),
                           currency='RUB',
                           prices=[LabeledPrice(label=f'Прогноз {ru_zodiac_sign}', amount=bot.price)],
                           provider_data=json.dumps({"capture": True})
                           )


@payments_router.pre_checkout_query(lambda query: True)
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery, bot: Bot):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@payments_router.message(F.successful_payment)
async def successful_payment(message: Message, state: FSMContext, bot: Bot):
    state_data = await state.get_data()
    ru_zodiac_sign = state_data['ru_zodiac_sign']

    await logging_successful_payment(message=message, state=state)
    await message.answer(
        f'Ваш платеж на сумму {message.successful_payment.total_amount // 100} '
        f'прошел успешно. Ниже прикреплен файл с разбором')
    path = pathlib.Path(bot.data_path, f"{ru_zodiac_sign}.pdf")
    await message.answer_document(FSInputFile(path=path))


async def logging_successful_payment(message: Message, state: FSMContext) -> None:
    state_data = await state.get_data()
    en_zodiac_sign = state_data['en_zodiac_sign']
    ru_zodiac_sign = state_data['ru_zodiac_sign']

    log_payment_data = {
        'datetime': datetime.now().strftime('%Y-%m-%d_%H-%M-%S'),
        'user': {
            'user_id': message.from_user.id,
            'username': message.from_user.username,
            'first_name': message.from_user.first_name,
            'last_name': message.from_user.last_name
        },
        'zodiac_sign': {
            'ru_zodiac_sign': ru_zodiac_sign,
            'en_zodiac_sign': en_zodiac_sign
        },
        'payment_data': {
            'currency': message.successful_payment.currency,
            'amount': message.successful_payment.total_amount // 100,
            'invoice': message.successful_payment.invoice_payload,
            'telegram payment id': message.successful_payment.telegram_payment_charge_id,
            'provider payment in': message.successful_payment.provider_payment_charge_id,
            'shipping option': message.successful_payment.shipping_option_id,
            'order_info': message.successful_payment.order_info
        },
    }

    payment_loger.log(15, json.dumps(log_payment_data, ensure_ascii=False))
