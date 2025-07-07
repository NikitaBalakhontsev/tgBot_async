import asyncio
import json
import os
import logging
import random
import re

from datetime import datetime as datetime, date
from aiogram import F, Router, Bot
from aiogram.filters import CommandStart, StateFilter, Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery, InlineKeyboardMarkup, \
    InlineKeyboardButton

import bot.keyboards as kb
from bot.config import ZODIAC_BTNS
from bot.utils.json_store import save_user_data, load_user_data

user_private_router = Router()
payment_loger = logging.getLogger('payment')


# Отключить админам базовый сценарий бота
# user_private_router.message.filter(ChatTypeFilter(["private"]), ~IsAdmin())
def gform(gender: str, female: str, male: str) -> str:
    return female if gender == "Женский" else male

class Customer(StatesGroup):
    start = State()
    #zodiac_sign = State()
    ask_gender = State()
    wait_gender = State()
    ask_birthdate = State()
    wait_birthdate = State()
    ask_feeling = State()
    wait_feeling = State()
    forecast = State()



@user_private_router.message(StateFilter(None))
@user_private_router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot, state: FSMContext):
    await state.clear()

    user_id = str(message.chat.id)
    user_data = load_user_data()
    # if user_data.get(user_id, {}).get("first_forecast_date"):
    #     await message.answer("🔁 Сеанс уже был начат ранее. Ожидай новый прогноз в ближайшее время.")
    #     return

    await message.answer("<b>Связь установлена...</b>", parse_mode="HTML")

    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    await asyncio.sleep(random.uniform(3.0, 5.0))
    await message.answer(
        "Привет. Меня зовут <b>Астра</b> — я читаю знаки неба и могу стать переводчиком между твоей картой рождения и настоящим моментом.",
        parse_mode="HTML"
    )

    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    await asyncio.sleep(random.uniform(3.0, 5.0))
    await message.answer(
        "Чтобы я могла раскрыть твой путь, ответь на <b>несколько вопросов</b>. Это нужно, чтобы рассчитать твой <b>астрологический профиль</b>.",
        parse_mode="HTML"
    )

    await state.set_state(Customer.ask_gender)
    await display_genders(message=message, state=state)

# @user_private_router.callback_query(StateFilter(Customer.start), F.data == 'predict')
# @user_private_router.callback_query(F.data == 'new_predict')
# @user_private_router.callback_query(StateFilter(Customer.confirm), F.data == 'zodiac_sign_change')
# async def display_zodiac_signs(callback: CallbackQuery, state: FSMContext):
#     await callback.answer('')
#
#     zodiac_btns = ZODIAC_BTNS.copy()
#     text = 'ㅤㅤㅤㅤВыберите знак зодиакаㅤㅤㅤ'
#     reply_markup = kb.get_callback_btns(btns=zodiac_btns)
#
#     if callback.data == 'zodiac_sign_change':
#         await callback.message.edit_text(text=text, reply_markup=reply_markup)
#     else:
#         await state.set_state(Customer.zodiac_sign)
#         await callback.message.answer(text=text, reply_markup=reply_markup)


# @user_private_router.callback_query(StateFilter(Customer.zodiac_sign, Customer.confirm), F.data.in_(ZODIAC_BTNS.values()))
# async def handle_zodiac_sign(callback: CallbackQuery, state: FSMContext, bot: Bot):
#     zodiac_sign = callback.data
#
#     await callback.answer('')
#     await state.update_data(zodiac_sign=zodiac_sign)
#
#     if (await state.get_state() == Customer.confirm):
#         await state.set_state(Customer.confirm)
#         await confirm_data(message=callback.message, state=state, bot=bot, edit_text=True)
#     else:
#         await callback.message.edit_text(text="ㅤㅤㅤㅤВыбран знак зодиакаㅤㅤㅤ", reply_markup=kb.get_callback_btns(
#             btns={
#                 zodiac_sign: "None"
#             }))
#         await state.set_state(Customer.gender)
#         await display_genders(callback=callback, state=state)


@user_private_router.callback_query(StateFilter(Customer.ask_gender), F.data == 'gender_change')
async def display_genders(message: Message | CallbackQuery, state: FSMContext):
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    await asyncio.sleep(random.uniform(2.5, 5.0))

    text = "Укажи свой пол"
    reply_markup = kb.get_callback_btns(
        btns={
            'Женский': 'Женский',
            'Мужской': 'Мужской',
        })

    await state.set_state(Customer.wait_gender)
    if isinstance(message, CallbackQuery):
        await message.answer('')
        try:
            await message.message.edit_text(text=text, reply_markup=reply_markup)
        except Exception:
            await message.message.answer(text=text, reply_markup=reply_markup)
    else:
        await message.answer(text=text, reply_markup=reply_markup)


@user_private_router.callback_query(StateFilter(Customer.wait_gender), F.data.in_({'Женский', 'Мужской'}))
async def handle_gender(callback: CallbackQuery, state: FSMContext, bot):
    gender = callback.data

    await callback.answer('')
    await callback.message.edit_text(text="Указан пол", reply_markup=kb.get_callback_btns(
        btns={
            gender: 'None'
        }))

    await state.update_data(gender=gender)

    data = await state.get_data()
    await save_user_data(callback.from_user.id, data)

    # if (await state.get_state() == Customer.confirm):
    #     await state.set_state(Customer.confirm)
    #     await confirm_data(message=callback.message, state=state, bot=bot, edit_text=True)
    # else:
    await state.set_state(Customer.ask_birthdate)
    await ask_birthdate(message=callback.message, state=state)



@user_private_router.message(Customer.ask_birthdate)
async def ask_birthdate(message: Message, state: FSMContext):
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    await asyncio.sleep(random.uniform(2.5, 5.0))
    state_data = await state.get_data()

    await message.answer(
        text=(
            f"Когда ты {gform(state_data['gender'], 'появилась', 'появился')} на свет?"
            "\nВведи дату в формате <b><code>ДД.ММ.ГГГГ</code></b>"
        ),
        parse_mode="HTML"
    )
    await state.set_state(Customer.wait_birthdate)

@user_private_router.message(Customer.wait_birthdate)
async def handle_birthdate(message: Message, state: FSMContext, bot: Bot):
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    await asyncio.sleep(random.uniform(2.0, 3.0))
    raw = message.text.strip()

    match = re.search(r'(\d{2})[.,](\d{2})[.,](\d{4})', raw)
    if not match:
        await message.answer("Не получилось распознать дату 😕\nПопробуй снова: <code>ДД.ММ.ГГГГ</code>", parse_mode="HTML")
        return

    day, month, year = map(int, match.groups())

    try:
        birth_date = datetime(year, month, day).date()
    except ValueError:
        await message.answer("Такой даты не существует. Попробуй снова: <code>ДД.ММ.ГГГГ</code>", parse_mode="HTML")
        return

        # 🔍 Проверка диапазона допустимых дат
    min_date = date(1940, 1, 1)
    max_date = date(datetime.now().year - 3, 12, 31)

    if not (min_date <= birth_date <= max_date):
        await message.answer(
            f"Пожалуйста, укажи дату рождения между {min_date.strftime('%d.%m.%Y')} и {max_date.strftime('%d.%m.%Y')}.",
            parse_mode="HTML"
        )
        return

    sign = get_zodiac_sign(day, month)

    await state.update_data(birthdate=birth_date.isoformat(), zodiac_sign=sign)

    data = await state.get_data()
    await save_user_data(message.from_user.id, data)

    await message.answer(
        f"Дата рождения обработана: <b>{birth_date.strftime('%d.%m.%Y')}</b>\n"
        f"Твой знак зодиака: <b>{sign}</b>",
        parse_mode="HTML"
    )

    await state.set_state(Customer.ask_feeling)
    await ask_feeling(message=message, state=state)

def get_zodiac_sign(day: int, month: int) -> str | None:
    signs = [
        ("Козерог", (1, 1), (1, 19)),
        ("Водолей", (1, 20), (2, 18)),
        ("Рыбы", (2, 19), (3, 20)),
        ("Овен", (3, 21), (4, 19)),
        ("Телец", (4, 20), (5, 20)),
        ("Близнецы", (5, 21), (6, 20)),
        ("Рак", (6, 21), (7, 22)),
        ("Лев", (7, 23), (8, 22)),
        ("Дева", (8, 23), (9, 22)),
        ("Весы", (9, 23), (10, 22)),
        ("Скорпион", (10, 23), (11, 21)),
        ("Стрелец", (11, 22), (12, 21)),
        ("Козерог", (12, 22), (12, 31)),  # Козерог встречается два раза – начало и конец года
    ]
    for sign, (start_m, start_d), (end_m, end_d) in signs:
        if (month == start_m and day >= start_d) or (month == end_m and day <= end_d):
            return sign
    return None


@user_private_router.message(Customer.ask_feeling)
async def ask_feeling(message: Message, state: FSMContext):
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    await asyncio.sleep(random.uniform(2.5, 5.0))
    await message.answer(
        "🕯️ Прежде чем я загляну в твою карту, мне важно почувствовать, с чего начать."
    )

    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    await asyncio.sleep(random.uniform(2.5, 5.0))
    await message.answer(
        "Каждый день мы проживаем что-то своё — и даже звёзды звучат по-разному, когда мы на пределе или наоборот, полны сил."
    )

    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    await asyncio.sleep(random.uniform(2.5, 5.0))
    await message.answer(
        "Поэтому скажи честно:"
    )

    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    await asyncio.sleep(random.uniform(2, 5.0))
    await message.answer("Как ты себя сейчас чувствуешь?")
    await state.set_state(Customer.wait_feeling)


@user_private_router.message(Customer.wait_feeling)
async def wait_feeling(message: Message, state: FSMContext):
    user_id = message.from_user.id
    feeling = message.text.strip()

    # Сохраняем самочувствие
    await state.update_data(feeling=feeling)

    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    await asyncio.sleep(random.uniform(2.5, 5.0))
    await message.answer(
        "Спасибо, что поделился этим.\nЯ знаю, что даже один честный ответ себе — уже шаг к ясности."
    )

    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    await asyncio.sleep(random.uniform(2.5, 5.0))
    await message.answer(
        "Небо бывает разным — и сегодня оно звучит именно для тебя. Я уже заглянула в твою карту и готовлю послание звёзд."
    )

    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    await asyncio.sleep(random.uniform(2.5, 5.0))
    await message.answer("Секундочку...")


    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    await asyncio.sleep(random.uniform(4.0, 8.0))

    # Получаем знак зодиака
    data = await state.get_data()
    zodiac_sign = data.get("zodiac_sign")

    # Отправляем гороскоп
    await send_forecast_message(
        user_id=user_id,
        zodiac_sign=zodiac_sign,
        bot=message.bot,
        as_reply=True
    )

    # Сохраняем дату первой отправки
    today_str = date.today().isoformat()
    await state.update_data(first_forecast_date=today_str)

    # Обновляем JSON-данные
    data = await state.get_data()
    await save_user_data(user_id, data)

    await state.set_state(Customer.forecast)




# @user_private_router.message(StateFilter(Customer.year, Customer.confirm), F.text.regexp(r'\d{4}'))
# async def handle_valid_year(message: Message, state: FSMContext, bot: Bot):
#     year = int(message.text)
#     if (1940 <= year <= datetime.now().year):
#         await state.update_data(year=year)
#         await state.set_state(Customer.confirm)
#         await confirm_data(message=message, state=state, bot=bot)
#     else:
#         age = datetime.now().year - year
#         await message.answer(text=f"Ваш возраст действительно {age} ?, отправьте новую дату")
#
# @user_private_router.message(StateFilter(Customer.year))
# async def display_years(message: Message):
#     await message.answer(text="Идем дальше. Отправьте сообщение с годом рождения \n"
#                               "формат:ㅤ4 цифры")

# async def confirm_data(message: Message, state: FSMContext, bot: Bot, edit_text: bool = False):
#     state_data = await state.get_data()
#
#     text = (f"Прогноз почти у вас, подтвердите данные \n"
#             f"Знак.ㅤㅤㅤㅤㅤㅤㅤ <b>{state_data['zodiac_sign']}</b> \n"
#             f"Полㅤㅤㅤㅤㅤㅤㅤㅤ<b>{state_data['gender']}</b> \n"
#             f"Год рождения_ㅤ ㅤ<b>{state_data['year']}</b> \n"
#             f"Сумма платежаㅤㅤ<b>{bot.price // 100}</b>")
#
#     reply_markup = kb.get_callback_btns(
#         btns={
#             'Подтвердить': 'confirm_btn',
#             'Изменить': 'change_btn'
#         })
#
#     if edit_text:
#         await message.edit_text(text=text, reply_markup=reply_markup)
#     else:
#         await message.answer(text=text, reply_markup=reply_markup)
#
#
# @user_private_router.callback_query(StateFilter(Customer.confirm), F.data == 'change_btn')
# async def back_bth_confirm(callback: CallbackQuery, state: FSMContext):
#     await callback.answer(text='')
#
#     state_data = await state.get_data()
#     await state.set_state(Customer.confirm)
#     await callback.message.edit_text(text=f"Чтобы изменить данные нажмите соответсвующую кнопку \n"
#                                           f"Знак.ㅤㅤㅤㅤㅤㅤㅤ <b>{state_data['zodiac_sign']}</b> \n"
#                                           f"Полㅤㅤㅤㅤㅤㅤㅤㅤ<b>{state_data['gender']}</b> \n"
#                                           f"Год рождения_ㅤ ㅤ<b>{state_data['year']}</b> \n"
#                                      , reply_markup=kb.get_callback_btns(
#             btns={
#                 'Изменить знак зодиака': 'zodiac_sign_change',
#                 'Изменить пол': 'gender_change',
#                 'Изменить год рождения': 'year_change'
#             }, sizes=[1, 1, 1]))


# @user_private_router.callback_query(StateFilter(Customer.confirm), F.data == 'year_change')
# async def callback_year_change(callback: CallbackQuery):
#     await callback.answer('')
#     await callback.message.edit_reply_markup(reply_markup=kb.get_callback_btns(
#         btns={
#             "Изменить год рождения": "None"
#         }))
#     await callback.message.answer(text="Отправьте сообщение с годом рождения\n"
#                                           "формат:ㅤ4 цифры")
#
#     await display_years(callback=callback)


async def send_forecast_message(user_id: int, zodiac_sign: str, bot: Bot, as_reply: bool = False):
    file = bot.file_system.get_file(sign="general_queue")

    if not file:
        logging.error(f"{user_id}: Не найден файл для знака {zodiac_sign}")
        return

    try:
        await bot.send_document(chat_id=user_id, document=file, protect_content=True)

        if as_reply:
            await bot.send_message(
                chat_id=user_id,
                text="Твой гороскоп на сегодня 🪐\n(файл прикреплён выше)",
                reply_markup=kb.get_callback_btns(
                    btns={'Получить подробный прогноз': 'pay_forecast'}
                )
            )
        else:
            await bot.send_message(
                chat_id=user_id,
                text="Привет!\nНаступил новый день, а значит время новый открытий! \nТвой гороскоп на сегодня 🪐\n(файл прикреплён выше)",
                reply_markup=kb.get_callback_btns(
                    btns={'Получить подробный прогноз': 'pay_forecast'}
                )
            )
    except Exception as e:
        logging.error(f"Ошибка при отправке гороскопа пользователю {user_id}: {e}", exc_info=True)


payments_router = Router()


@payments_router.callback_query(F.data == 'pay_forecast')
async def send_invoice_handler(callback: CallbackQuery, bot: Bot, state: FSMContext):
    await callback.answer()  # убираем "часики"

    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        title="🔮 Подробный персональный гороскоп",
        description=f"Звёзды говорят — и у них есть послание для тебя",
        payload='invoice_personal_forecast',
        provider_token="",
        currency='XTR',
        prices=[LabeledPrice(label="XTR", amount=bot.price)],
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=f"Получить послание {bot.price} ⭐️", pay=True)]
            ]
        )
    )

@payments_router.pre_checkout_query(lambda query: True)
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery, bot: Bot):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@payments_router.message(F.successful_payment)
async def successful_payment(message: Message, state: FSMContext, bot: Bot):
    user_id = message.chat.id

    # Попытка получить знак из FSM-состояния
    try:
        data = await state.get_data()
        zodiac_sign = data.get("zodiac_sign")
        user_data = load_user_data().get(str(user_id))
        zodiac_sign = user_data.get("zodiac_sign") if user_data else None
    except Exception:
        await bot.send_message(
            1054042861,  # ID администратора
            f"⚠️ Не удалось определить знак зодиака для пользователя {user_id} после оплаты."
        )
        await message.answer(
            "Произошла ошибка при обработке вашего заказа. Мы уже работаем над этим.")
        return

    # Если знак зодиака так и не найден
    if not zodiac_sign:
        await bot.send_message(
            1054042861,  # ID администратора
            f"⚠️ Не удалось определить знак зодиака для пользователя {user_id} после оплаты."
        )
        await message.answer(
            "Произошла ошибка при обработке вашего заказа. Мы уже работаем над этим.")
        return

    # Попытка отправки файла
    try:
        file = bot.file_system.get_file(zodiac_sign, kind="detailed")
        if not file:
            raise ValueError(f"Файл не найден для знака зодиака: {zodiac_sign}")

        await bot.send_document(chat_id=user_id, document=file, protect_content=True)
        await message.answer(
            text=(
                "✨ Оплата прошла успешно!\n"
                "Твой <b>подробный персональный гороскоп</b> прикреплён выше.\n\n"
                "Возвращайся завтра за новым посланием от звёзд 🌌"
            )
        )
    except Exception as e:
        await bot.send_message(
            1054042861,
            f"⚠️ Не удалось отправить файл гороскопа для пользователя {user_id} ({zodiac_sign}).\nОшибка: {e}"
        )
        await message.answer("Произошла ошибка при отправке файла. Мы скоро с вами свяжемся.")





# async def logging_successful_payment(message: Message, state: FSMContext, is_real=True) -> None:
#     state_data = await state.get_data()
#     zodiac_sign = state_data['zodiac_sign']
#
#     log_payment_data = {
#         'datetime': datetime.now().strftime('%Y-%m-%d_%H-%M-%S'),
#         'user': {
#             'user_id': message.from_user.id,
#             'username': message.from_user.username,
#             'first_name': message.from_user.first_name,
#             'last_name': message.from_user.last_name
#         },
#         'zodiac_sign': zodiac_sign
#     }
#
#     if is_real:
#         log_payment_data['payment_data']: {
#             'currency': message.successful_payment.currency,
#             'amount': message.successful_payment.total_amount // 100,
#             'invoice': message.successful_payment.invoice_payload,
#             'telegram payment id': message.successful_payment.telegram_payment_charge_id,
#             'provider payment in': message.successful_payment.provider_payment_charge_id,
#             'shipping option': message.successful_payment.shipping_option_id,
#             'order_info': message.successful_payment.order_info
#         }
#
#     payment_loger.log(15, json.dumps(log_payment_data, ensure_ascii=False))
