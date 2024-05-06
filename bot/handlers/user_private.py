import json
import os
import logging

from datetime import datetime as datetime
from aiogram import F, Router, Bot
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery

import bot.keyboards as kb
from bot.config import ZODIAC_BTNS

user_private_router = Router()
payment_loger = logging.getLogger('payment')


# Отключить админам базовый сценарий бота
# user_private_router.message.filter(ChatTypeFilter(["private"]), ~IsAdmin())

class Customer(StatesGroup):
    start = State()
    zodiac_sign = State()
    gender = State()
    year = State()
    confirm = State()


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
        await message.answer(f"Рад, что смог заинтересовать вас, для начала работы подпишитесь на канал {invite_link}")

    else:
        await message.answer('Добрый день! Я ваш персональный астрологический помощник.',
                             reply_markup=kb.get_callback_btns(
                                 btns={
                                    'Получить прогноз': 'predict'
                                 }))
        await state.clear()
        await state.set_state(Customer.start)

@user_private_router.callback_query(StateFilter(Customer.start), F.data == 'predict')
@user_private_router.callback_query(F.data == 'new_predict')
@user_private_router.callback_query(StateFilter(Customer.confirm), F.data == 'zodiac_sign_change')
async def display_zodiac_signs(callback: CallbackQuery, state: FSMContext):
    await callback.answer('')

    zodiac_btns = ZODIAC_BTNS.copy()
    text = 'ㅤㅤㅤㅤВыберите знак зодиакаㅤㅤㅤ'
    reply_markup = kb.get_callback_btns(btns=zodiac_btns)

    if callback.data == 'zodiac_sign_change':
        await callback.message.edit_text(text=text, reply_markup=reply_markup)
    else:
        await state.set_state(Customer.zodiac_sign)
        await callback.message.answer(text=text, reply_markup=reply_markup)


@user_private_router.callback_query(StateFilter(Customer.zodiac_sign, Customer.confirm), F.data.in_(ZODIAC_BTNS.values()))
async def handle_zodiac_sign(callback: CallbackQuery, state: FSMContext, bot: Bot):
    zodiac_sign = callback.data

    await callback.answer('')
    await state.update_data(zodiac_sign=zodiac_sign)

    if (await state.get_state() == Customer.confirm):
        await state.set_state(Customer.confirm)
        await confirm_data(message=callback.message, state=state, bot=bot, edit_text=True)
    else:
        await callback.message.edit_text(text="ㅤㅤㅤㅤВыбран знак зодиакаㅤㅤㅤ", reply_markup=kb.get_callback_btns(
            btns={
                zodiac_sign: "None"
            }))
        await state.set_state(Customer.gender)
        await display_genders(callback=callback, state=state)


@user_private_router.callback_query(StateFilter(Customer.confirm), F.data == 'gender_change')
async def display_genders(callback: CallbackQuery, state: FSMContext):
    text = "ㅤㅤㅤㅤㅤㅤУкажите полㅤㅤㅤㅤㅤㅤ"
    reply_markup = kb.get_callback_btns(
        btns={
            'Женский': 'Женский',
            'Мужской': 'Мужской',
        })

    if (await state.get_state() == Customer.confirm):
        await callback.answer('')
        await callback.message.edit_text(text=text, reply_markup=reply_markup)
    else:

        await callback.message.answer(text=text, reply_markup=reply_markup)


@user_private_router.callback_query(StateFilter(Customer.gender, Customer.confirm), F.data.in_({'Женский', 'Мужской'}))
async def handle_gender(callback: CallbackQuery, state: FSMContext, bot):
    gender = callback.data

    await callback.answer('')
    await callback.message.edit_text(text="ㅤㅤㅤㅤㅤㅤУказан полㅤㅤㅤㅤㅤㅤㅤ", reply_markup=kb.get_callback_btns(
        btns={
            gender: 'None'
        }))

    await state.update_data(gender=gender)

    if (await state.get_state() == Customer.confirm):
        await state.set_state(Customer.confirm)
        await confirm_data(message=callback.message, state=state, bot=bot, edit_text=True)
    else:
        await state.set_state(Customer.year)
        await display_years(message=callback.message)

@user_private_router.message(StateFilter(Customer.year, Customer.confirm), F.text.regexp(r'\d{4}'))
async def handle_valid_year(message: Message, state: FSMContext, bot: Bot):
    year = int(message.text)
    if (1940 <= year <= datetime.now().year):
        await state.update_data(year=year)
        await state.set_state(Customer.confirm)
        await confirm_data(message=message, state=state, bot=bot)
    else:
        age = datetime.now().year - year
        await message.answer(text=f"Ваш возраст действительно {age} ?, отправьте новую дату")

@user_private_router.message(StateFilter(Customer.year))
async def display_years(message: Message):
    await message.answer(text="Идем дальше. Отправьте сообщение с годом рождения \n"
                              "формат:ㅤ4 цифры")

async def confirm_data(message: Message, state: FSMContext, bot: Bot, edit_text: bool = False):
    state_data = await state.get_data()

    text = (f"Прогноз почти у вас, подтвердите данные \n"
            f"Знак.ㅤㅤㅤㅤㅤㅤㅤ <b>{state_data['zodiac_sign']}</b> \n"
            f"Полㅤㅤㅤㅤㅤㅤㅤㅤ<b>{state_data['gender']}</b> \n"
            f"Год рождения_ㅤ ㅤ<b>{state_data['year']}</b> \n"
            f"Сумма платежаㅤㅤ<b>{bot.price // 100}</b>")

    reply_markup = kb.get_callback_btns(
        btns={
            'Подтвердить': 'confirm_btn',
            'Изменить': 'change_btn'
        })

    if edit_text:
        await message.edit_text(text=text, reply_markup=reply_markup)
    else:
        await message.answer(text=text, reply_markup=reply_markup)


@user_private_router.callback_query(StateFilter(Customer.confirm), F.data == 'change_btn')
async def back_bth_confirm(callback: CallbackQuery, state: FSMContext):
    await callback.answer(text='')

    state_data = await state.get_data()
    await state.set_state(Customer.confirm)
    await callback.message.edit_text(text=f"Чтобы изменить данные нажмите соответсвующую кнопку \n"
                                          f"Знак.ㅤㅤㅤㅤㅤㅤㅤ <b>{state_data['zodiac_sign']}</b> \n"
                                          f"Полㅤㅤㅤㅤㅤㅤㅤㅤ<b>{state_data['gender']}</b> \n"
                                          f"Год рождения_ㅤ ㅤ<b>{state_data['year']}</b> \n"
                                     , reply_markup=kb.get_callback_btns(
            btns={
                'Изменить знак зодиака': 'zodiac_sign_change',
                'Изменить пол': 'gender_change',
                'Изменить год рождения': 'year_change'
            }, sizes=[1, 1, 1]))


@user_private_router.callback_query(StateFilter(Customer.confirm), F.data == 'year_change')
async def callback_year_change(callback: CallbackQuery):
    await callback.answer('')
    await callback.message.edit_reply_markup(reply_markup=kb.get_callback_btns(
        btns={
            "Изменить год рождения": "None"
        }))
    await callback.message.answer(text="Отправьте сообщение с годом рождения\n"
                                          "формат:ㅤ4 цифры")

    await display_years(callback=callback)


payments_router = Router()


@payments_router.callback_query(StateFilter(Customer.confirm), F.data == 'confirm_btn')
async def order(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer('')
    await callback.message.edit_reply_markup(reply_markup=kb.get_callback_btns(
        btns={
            'Подтверждено': 'None'
        }))

    state_data = await state.get_data()
    zodiac_sign = state_data['zodiac_sign']

    if bot.price == 0:
        await successful_payment(message=callback.message, bot=bot, state=state)
    else:
        await bot.send_invoice(callback.message.chat.id,
                               title='Прогноз',
                               description=f"Ты узнаешь все о {zodiac_sign}",
                               payload='invoice',
                               provider_token=os.getenv('PAYMENT_TOKEN_TEST'),
                               currency='RUB',
                               prices=[LabeledPrice(label=f"Прогноз {zodiac_sign}", amount=bot.price)],
                               provider_data=json.dumps({"capture": True})
                               )


@payments_router.pre_checkout_query(lambda query: True)
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery, bot: Bot):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@payments_router.message(F.successful_payment)
async def successful_payment(message: Message, state: FSMContext, bot: Bot):
    state_data = await state.get_data()
    zodiac_sign = state_data['zodiac_sign']
    file = bot.file_system.get_file(zodiac_sign)

    if bot.price == 0:
        await logging_successful_payment(message=message, state=state, is_real=False)
        await bot.send_document(chat_id=message.chat.id, document=file, protect_content=True)
        await message.answer(
            text=f"Вы успешно воспользовались акцией. \n"
                 f"Оставайтесь с нами для получения новых прогнозов\n"
                 f"(файл с подробным прогнозом прикреплен выше)",
            reply_markup=kb.get_callback_btns(
                btns={
                    'Получить новый прогноз': 'new_predict'
                }))

    else:
        await logging_successful_payment(message=message, state=state)
        await bot.send_document(chat_id=message.chat.id, document=file, protect_content=True)
        await message.answer(
            text=f"Опалата на сумму {message.successful_payment.total_amount // 100} прошла успешно\n"
                 f"Оставайтесь с нами для получения новых прогнозов)\n"
                 f""f"(файл с подробным прогнозом прикреплен выше)",
            reply_markup=kb.get_callback_btns(
                btns={
                    'Получить новый прогноз': 'new_predict'
                }))

    await state.clear()
    await state.set_state(Customer.start)


async def logging_successful_payment(message: Message, state: FSMContext, is_real=True) -> None:
    state_data = await state.get_data()
    zodiac_sign = state_data['zodiac_sign']

    log_payment_data = {
        'datetime': datetime.now().strftime('%Y-%m-%d_%H-%M-%S'),
        'user': {
            'user_id': message.from_user.id,
            'username': message.from_user.username,
            'first_name': message.from_user.first_name,
            'last_name': message.from_user.last_name
        },
        'zodiac_sign': zodiac_sign
    }

    if is_real:
        log_payment_data['payment_data']: {
            'currency': message.successful_payment.currency,
            'amount': message.successful_payment.total_amount // 100,
            'invoice': message.successful_payment.invoice_payload,
            'telegram payment id': message.successful_payment.telegram_payment_charge_id,
            'provider payment in': message.successful_payment.provider_payment_charge_id,
            'shipping option': message.successful_payment.shipping_option_id,
            'order_info': message.successful_payment.order_info
        }

    payment_loger.log(15, json.dumps(log_payment_data, ensure_ascii=False))
