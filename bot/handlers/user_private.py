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
    zodiac_sign = State()
    gender = State()
    year = State()
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
        await message.answer(f'Рад, что смог заинтересовать вас, для начала работы подпишитесь на канал {invite_link}')

    else:
        await message.answer('Добрый день! Я ваш персональный астрологический помощник.',
                             reply_markup=kb.get_callback_btns(btns={
                                 'Получить прогноз': 'predict'
                             }))
        await state.clear()
        await state.set_state(Customer.start)


'''
@user_private_router.message(StateFilter(Customer.start), F.photo)
async def doc_save(message: Message, state: FSMContext, bot: Bot):
    print(message.photo)
'''

@user_private_router.callback_query(StateFilter(Customer.start), F.data == 'predict')
@user_private_router.callback_query(StateFilter(Customer.start), F.data == 'new_predict')
@user_private_router.callback_query(StateFilter(Customer.confirm), F.data == 'zodiac_sign_change')
async def display_zodiac_signs(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer('')

    zodiac_btns = {sign['ru']: sign['en'] for sign in bot.zodiac_signs}
    text = 'Выбери знак зодиака'
    reply_markup = kb.get_callback_btns(btns=zodiac_btns)

    if callback.data == 'zodiac_sign_change':
        await callback.message.edit_text(text=text, reply_markup=reply_markup)
    else:
        await state.set_state(Customer.zodiac_sign)
        await callback.message.answer(text=text, reply_markup=reply_markup)


@user_private_router.callback_query(StateFilter(Customer.zodiac_sign, Customer.confirm), F.data.in_({
    'aries', 'taurus', 'gemini', 'cancer', 'leo', 'virgo', 'libra', 'scorpio', 'sagittarius',
    'capricorn', 'aquarius', 'pisces'}))
async def handle_zodiac_sign(callback: CallbackQuery, state: FSMContext, bot: Bot):
    en_zodiac_sign = callback.data
    ru_zodiac_sign = None
    for sign in bot.zodiac_signs:
        if sign['en'] == en_zodiac_sign:
            ru_zodiac_sign = sign['ru']

    await callback.answer('')
    await state.update_data(ru_zodiac_sign=ru_zodiac_sign, en_zodiac_sign=en_zodiac_sign)

    if (await state.get_state() == Customer.confirm):
        await state.set_state(Customer.confirm)
        await confirm_data(message=callback.message, state=state, bot=bot, edit_text=True)
    else:
        await state.set_state(Customer.gender)
        await display_genders(callback=callback)

@user_private_router.callback_query(StateFilter(Customer.confirm), F.data == 'gender_change')
async def display_genders(callback: CallbackQuery):
    await callback.message.edit_text(text='Супер, теперь укажи свой гендер', reply_markup=kb.get_callback_btns(btns={
        'Женщина': 'Женщина',
        'Мужчина': 'Мужчина',
        'Другое': 'Другой'
    }))


@user_private_router.callback_query(StateFilter(Customer.gender, Customer.confirm), F.data.in_({'Женщина', 'Мужчина', 'Другой'}))
async def handle_gender(callback: CallbackQuery, state: FSMContext, bot):
    gender = callback.data

    await callback.answer('')
    await callback.message.edit_reply_markup(reply_markup=kb.get_callback_btns(btns={
        gender: 'None'
    }))

    await state.update_data(gender=gender)

    if (await state.get_state() == Customer.confirm):
        await state.set_state(Customer.confirm)
        await confirm_data(message=callback.message, state=state, bot=bot, edit_text=True)
    else:
        await state.set_state(Customer.year)
        await display_years(callback=callback)


async def display_years(callback: CallbackQuery):
    file_id = 'AgACAgIAAxkBAAOmZjT4cHsqjVzpro_nmeEZR9s3Ng0AAsPYMRuv5KhJAZglKGYNQFQBAAMCAANtAAM0BA'
    await callback.message.answer_photo(photo=file_id,
                               caption=f'Остался год рождения. Отправьте мне сообщение с годом рождения (4 цифры)')


@user_private_router.message(StateFilter(Customer.year, Customer.confirm), F.text.regexp(r'\d{4}'))
async def handle_valid_year(message: Message, state: FSMContext, bot: Bot):
    year = int(message.text)
    if (1940 <= year <= datetime.now().year):
        await state.update_data(year=year)
        await state.set_state(Customer.confirm)
        await confirm_data(message=message, state=state, bot=bot)
    else:
        age = datetime.now().year - year
        await message.answer(text=f'Ваш возраст действительно {age} ?, отправьте новую дату')


@user_private_router.message(StateFilter(Customer.year))
async def handle_invalid_year(message: Message, bot: Bot):
    await message.answer(text=f'Получено  {message.text}.\n')
    await display_years(message=message, data_path=bot.data_path)


async def confirm_data(message: Message, state: FSMContext, bot: Bot, edit_text: bool = False):
    state_data = await state.get_data()

    text = (f'Прогноз почти у вас, остался последний шаг \n'
    f'Подтвердите данные \n'
    f'Знак зодиака <b>[ {state_data['ru_zodiac_sign']} ]</b> \n'
    f'Гендер <b>[ {state_data['gender']} ]</b> \n'
    f'Год рождения <b>[ {state_data['year']} ]</b> \n'
    f'Сумма платежа <b>[ {bot.price // 100} ]</b>')

    reply_markup = kb.get_callback_btns(btns={
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
    await callback.message.edit_text(text=f'Чтобы изменить данные нажмите соответсвующую кнопку \n'
                                          f'Знак зодиака <b>[ {state_data['ru_zodiac_sign'] } ]</b> \n'
                                          f'Гендер <b>[ {state_data['gender'] } ]</b> \n'
                                          f'Год рождения <b>[ {state_data['year'] } ]</b> \n'
                                     ,reply_markup=kb.get_callback_btns(btns={
            'Изменить знак зодиака': 'zodiac_sign_change',
            'Изменить гендер': 'gender_change',
            'Изменить год рождения': 'year_change'
        }))


@user_private_router.callback_query(StateFilter(Customer.confirm), F.data == 'year_change')
async def callback_year_change(callback: CallbackQuery):
    await callback.answer('')
    await callback.message.edit_reply_markup(reply_markup=kb.get_callback_btns(btns={
        'Изменить год рождения': 'None'
    }))
    await display_years(callback=callback)



payments_router = Router()


@payments_router.callback_query(StateFilter(Customer.confirm), F.data == 'confirm_btn')
async def order(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer('')
    await callback.message.edit_reply_markup(reply_markup=kb.get_callback_btns(btns={
        'Подтверждено': 'None'
    }))

    state_data = await state.get_data()
    ru_zodiac_sign = state_data['ru_zodiac_sign']

    if bot.price == 0:
        await successful_payment(message=callback.message, bot=bot, state=state)
    else:
        await bot.send_invoice(callback.message.chat.id,
                               title='Прогноз',
                               description=f'Ты узнаешь все о {ru_zodiac_sign}',
                               payload='invoice',
                               provider_token=os.getenv('PAYMENT_TOKEN_TEST'),
                               currency='RUB',
                               prices=[LabeledPrice(label=f'Прогноз {ru_zodiac_sign}', amount=bot.price)],
                               provider_data=json.dumps({"capture": True})
                               )


@payments_router.pre_checkout_query(lambda query: True)
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery, bot: Bot):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


async def send_file(bot: Bot, chat_id: int, filename: str):
    file_id = bot.files_dict[filename]['id']
    file_path = bot.files_dict[filename]['path']

    if file_id:
        await bot.send_document(chat_id=chat_id, document=file_id)
        print(file_id)
    else:
        await bot.send_document(chat_id=chat_id, document=FSInputFile(file_path))


@payments_router.message(F.successful_payment)
async def successful_payment(message: Message, state: FSMContext, bot: Bot):
    state_data = await state.get_data()
    zodiac_sign = state_data['ru_zodiac_sign']

    if bot.price == 0:
        await logging_successful_payment(message=message, state=state, is_real=False)
        await message.answer(
            f'Вы успешно воспользовались акцией. \n'
            f'Оставайтесь с нами для получения новых прогнозов)\n'
            f'(файл с подробным прогнозом прикреплен ниже)',
            reply_markup=kb.get_callback_btns(btns={
                'Получить новый прогноз': 'new_predict'
            }))
        await send_file(bot=bot, chat_id=message.chat.id, filename=zodiac_sign)
    else:
        await logging_successful_payment(message=message, state=state)
        await message.answer(
            f'Опалата на сумму {message.successful_payment.total_amount // 100} прошла успешно\n'
            f'Оставайтесь с нами для получения новых прогнозов)\n'
            f'(файл с подробным прогнозом прикреплен ниже)', reply_markup=kb.get_callback_btns(btns={
                'Получить новый прогноз': 'new_predict'
            }))
        await send_file(bot=bot, chat_id=message.chat.id, filename=zodiac_sign)

    await state.clear()
    await state.set_state(Customer.start)


async def logging_successful_payment(message: Message, state: FSMContext, is_real=True) -> None:
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
        }
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


