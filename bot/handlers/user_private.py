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
from bot.config import ZODIAC_BTNS, ADMINS
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

    user_id = message.from_user.id
    user_data = load_user_data()
    if user_data.get(str(user_id), {}).get("first_forecast_date"):
        await message.answer("Вернемся с новым прогнозом в ближайшее время.")
        return

    data = {
        "first_name": message.from_user.first_name or "",
        "last_name": message.from_user.last_name or "",
        "username": message.from_user.username or ""
    }
    await save_user_data(user_id, data)

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

    today_str = date.today().isoformat()
    await state.update_data(first_forecast_date=today_str)

    # Обновляем JSON-данные
    data = await state.get_data()
    await save_user_data(message.from_user.id, data)

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
    image_data = bot.file_system.get_image(sign="general_queue")

    if not image_data:
        logging.error(f"{user_id}: Не найден файл очереди для {zodiac_sign}")
        await bot.send_message("Упс... Послание от звезд пока не готово. Пожалуйста, загляни позже — как только оно появится, я сразу поделюсь.")
        await notify_admins_about_user(bot=bot, user_id=user_id, text=f"⚠️ Не найден общий гороскоп для нового пользователя.")
        return

    image, text = image_data
    caption_intro = (
        "Привет!\nНаступил новый день, а значит время новых открытий! 🌅\n\n"
        if not as_reply else ""
    )
    caption = f"{caption_intro}{text or 'Твой гороскоп на сегодня 🪐'}"

    try:
        await bot.send_photo(
            chat_id=user_id,
            photo=image,
            caption=caption,
            reply_markup=kb.get_callback_btns(
                btns={'Получить подробный прогноз': 'pay_forecast'}
            ),
            protect_content=True
        )
    except Exception as e:
        logging.error(f"Ошибка отправки гороскопа пользователю {user_id}: {e}")


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
        pass

    # Если знак зодиака так и не найден
    if not zodiac_sign:
        await message.answer("Произошла ошибка при обработке вашего заказа. Мы уже работаем над этим.")
        await notify_admins_about_user(bot=bot, user_id=user_id, text=f"⚠️ Не удалось определить знак зодиака для отправки подробного гороскопа.")
        return

    # Попытка отправки файла
    try:
        # Сначала подтверждаем оплату
        await message.answer(
            text=(
                "✨ Оплата прошла успешно!\n"
                "Сейчас я пришлю твой <b>подробный персональный гороскоп</b> 🪐"
            ),
            parse_mode="HTML"
        )

        # Загружаем изображение и подпись
        image_data = bot.file_system.get_image(sign=zodiac_sign, kind="detailed")
        if not image_data:
            raise ValueError(f"Файл не найден для знака зодиака: {zodiac_sign}")

        image, caption = image_data
        caption = caption or f"Подробный прогноз для {zodiac_sign}"

        # Отправляем сам гороскоп
        await bot.send_photo(
            chat_id=user_id,
            photo=image,
            caption=caption,
            protect_content=True
        )
        await notify_admins_about_user(bot=bot, user_id=user_id, text=f"✅ Успешно отправлен подробный гороскоп.")


    except Exception as e:
        await message.answer("Произошла ошибка при отправке гороскопа. С вами скоро свяжется менеджер.")
        await notify_admins_about_user(bot=bot, user_id=user_id, text=f"⚠️ Не удалось отправить файл гороскопа().\nОшибка: {e}")


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


async def notify_admins_about_user(bot: Bot, text: str, user_id: int, parse_mode: str = "HTML"):

    user_data = load_user_data().get(str(user_id))
    if not user_data:
        user_info = f"👤 <code>{user_id}</code> — <i>данные пользователя не найдены</i>"
        zodiac_part = ""
    else:
        first_name = user_data.get("first_name", "")
        last_name = user_data.get("last_name", "")
        username = user_data.get("username")
        zodiac_sign = user_data.get("zodiac_sign", "не указан")

        full_name = " ".join(part for part in [first_name, last_name] if part).strip()
        username_display = f"@{username}" if username else ""
        parts = [f"<code>{user_id}</code>"]
        if full_name:
            parts.append(full_name)
        if username_display:
            parts.append(username_display)

        user_info = "👤 " + " — ".join(parts)
        zodiac_part = f"\n♈ Знак зодиака: <b>{zodiac_sign}</b>"

    message = f"{user_info}{zodiac_part}\n\n{text}"

    for admin_id in ADMINS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=message,
                parse_mode=parse_mode
            )
        except Exception:
            pass

async def notify_admins_general(bot: Bot, text: str, parse_mode: str = "HTML"):
    for admin_id in ADMINS:
        try:
            await bot.send_message(chat_id=admin_id, text=text, parse_mode=parse_mode)
        except Exception:
            pass
