import asyncio
import os
import re
from pathlib import Path
from typing import Optional

from aiogram import F, Router, Bot
from aiogram.filters import Command, StateFilter, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove, FSInputFile
from aiogram.utils.formatting import as_marked_section

import bot.keyboards as kb
from bot.filters import ChatTypeFilter, IsAdmin
from bot.config import ZODIAC_BTNS, ZODIAC_SIGNS
from bot.utils.forecast import send_daily_forecasts, update_scheduler_time

"""
Используем отдельный роутер для управления диалогом с администратором.
Список администраторов хранится в bot.admin_list в формате user_id
"""
admin_router = Router()
admin_router.message.filter(ChatTypeFilter(["private"]), IsAdmin())


# Состояния для работы администратора
class Admin(StatesGroup):
    start = State()
    zodiac_sign = State()
    general_queue_menu = State()

    file_options = State()
    upload_file = State()

    price_options = State()
    request_price = State()

    broadcast_menu = State()
    broadcast_edit_time = State()

    path = None


# Запуск панели администратора
@admin_router.message(Command("admin"))
async def admin_cmd(message: Message, state: FSMContext):
    await message.answer(text="Запущена панель администратора", reply_markup=kb.get_reply_btns(
        "Изменить файлы",
        "Список файлов",
        "Управлять рассылкой",
        "Изменить цену",
        "Закрыть панель администратора",
        placeholder="Панель администратора",
        sizes=(2, 1, 1, 1)
    ))
    await state.set_state(Admin.start)



# Выбор знака зодиака для работы с файлами
@admin_router.message(StateFilter("*"), F.text.casefold() == "изменить файлы")
async def display_zodiac_signs(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(Admin.zodiac_sign)

    zodiac_btns = {"Общий гороскоп": "general_queue"}
    zodiac_btns.update(ZODIAC_BTNS)
    zodiac_btns['Назад'] = 'back_btn'

    await message.answer("Выбери знак зодиака:", reply_markup=kb.get_callback_btns(btns=zodiac_btns, sizes=(1, 2, 2, 2, 2, 2, 2, 1)))


@admin_router.callback_query(StateFilter(Admin.zodiac_sign), F.data.in_(ZODIAC_BTNS.values()))
async def select_zodiac_sign(callback: CallbackQuery, state: FSMContext, bot: Bot):
    zodiac_sign = callback.data

    await state.set_state(Admin.file_options)
    await state.update_data(file_source_type="zodiac_sign", zodiac_sign=zodiac_sign)

    await callback.message.delete()
    await display_file_options(
        message=callback.message,
        source_type="zodiac",
        bot=bot,
        state=state,
        sign=zodiac_sign,
    )


async def display_general_queue_menu_msg(message: Message, bot: Bot, state: FSMContext):
    await _display_general_queue_menu(message.chat.id, bot, state, send_method=bot.send_message)


@admin_router.callback_query(StateFilter(Admin.zodiac_sign), F.data == 'general_queue')
async def display_general_queue_menu_callback(callback: CallbackQuery, bot: Bot, state: FSMContext):
    await callback.message.delete()
    await _display_general_queue_menu(callback.message.chat.id, bot, state, send_method=bot.send_message)
    await callback.answer()


async def _display_general_queue_menu(chat_id: int, bot: Bot, state: FSMContext, send_method):
    files = bot.file_system.files.get("general_queue", [])
    await state.set_state(Admin.general_queue_menu)

    if not files:
        text = "Очередь пуста. Вы можете добавить новый файл."
    else:
        text = "<b>Очередь общих гороскопов:</b>\n\n"
        for idx, entry in enumerate(files):
            filename = Path(entry["path"]).name if entry.get("path") else "—"
            upload_date = entry.get("upload_date") or "—"
            text += f"{idx + 1}) <code>{filename}</code> — {upload_date}\n"

    buttons = {}
    for i, entry in enumerate(files):
        if entry.get("file_id") or entry.get("path"):
            buttons[f"{i + 1}"] = f"general_queue_{i}"
    if len(files) < 7:
        buttons["➕ Добавить файл"] = "add_general_queue"
    buttons["⬅️ Назад"] = "back_btn"

    await send_method(chat_id, text, reply_markup=kb.get_callback_btns(btns=buttons, sizes=(3, 3, 1)), parse_mode="HTML")



@admin_router.message(StateFilter(Admin.upload_file), F.document)
async def handle_upload(message: Message, state: FSMContext, bot: Bot):
    try:
        data = await state.get_data()
        file_id = message.document.file_id
        file_source_type = data.get("file_source_type")

        # Логика добавления в очередь или замены в очереди
        if file_source_type == "general_queue":
            queue_index = data.get("queue_index")

            # ЗАМЕНА файла в очереди
            if queue_index is not None:
                error = await bot.file_system.replace_general_file(index=queue_index, file_id=file_id)
                if error:
                    await message.answer(f"Ошибка при замене файла в очереди: {error}")
                else:
                    await message.answer(f"Файл очереди №{queue_index + 1} успешно обновлён.")
            else:
                # ДОБАВЛЕНИЕ нового файла в очередь
                current_length = len(bot.file_system.files["general_queue"]) + 1
                if current_length > 7:
                    await message.answer(
                        "⚠️ Очередь заполнена (максимум 7 файлов). Удалите или замените существующий файл.")
                    return

                error = await bot.file_system.add_file(
                    sign="general_queue",
                    file_id=file_id,
                    kind=current_length  # Индекс следующего свободного места
                )
                if error:
                    await message.answer(f"Ошибка при добавлении файла в очередь: {error}")
                else:
                    await message.answer(f"Файл успешно добавлен в очередь под номером {current_length}.")
            await display_general_queue_menu_msg(message=message, bot=bot, state=state)
            return

        # Загрузка для знака зодиака
        zodiac_sign = data.get("zodiac_sign")
        kind = data.get("kind", "detailed")
        if not zodiac_sign:
            await message.answer("Ошибка: знак зодиака не указан.")
            return

        error = await bot.file_system.add_file(sign=zodiac_sign, file_id=file_id, kind=kind)
        if error:
            await message.answer(f"Ошибка при сохранении файла: {error}")
        else:
            await message.answer(f"Файл '{kind}' для {zodiac_sign} успешно обновлён.")

        # Вернуться в меню работы с файлом
        # await display_file_options(message, bot, state, zodiac_sign)

    except Exception as e:
        await message.answer(f"Ошибка: {e}")


@admin_router.callback_query(StateFilter(Admin.general_queue_menu), F.data == "add_general_queue")
async def add_new_file_to_queue(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Admin.upload_file)
    await state.update_data(file_source_type="general_queue")

    await callback.message.edit_text(
        text="Отправьте новый файл для добавления в очередь общих гороскопов:",
        reply_markup=kb.get_callback_btns(btns={
            'Назад': 'back_btn'
        })
    )
    await callback.answer()


@admin_router.callback_query(StateFilter(Admin.upload_file), F.data == "back_btn")
async def cancel_upload_and_back(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    file_source_type = data.get("file_source_type")

    await callback.message.delete()

    if file_source_type == "general_queue":
        await display_general_queue_menu_callback(callback.message, bot, state)
    # else:
    #     await display_file_options(callback.message, bot, state, data.get("zodiac_sign"))


@admin_router.callback_query(StateFilter(Admin.general_queue_menu), F.data.startswith("general_queue_"))
async def edit_file_in_queue(callback: CallbackQuery, state: FSMContext, bot: Bot):
    index = int(callback.data.split("_")[-1])

    await state.set_state(Admin.file_options)
    await state.update_data(file_source_type="general_queue", queue_index=index)

    await callback.message.delete()
    await display_file_options(
        message=callback.message,
        bot=bot,
        state=state,
        source_type="general_queue",
        queue_index=index
    )
    await callback.answer()


async def display_file_options(message: Message, bot: Bot, state: FSMContext, source_type: str, sign: Optional[str] = None, queue_index: Optional[int] = None):
    """
    Универсальное меню работы с файлом: показать информацию и действия (скачать, заменить).
    :param message: объект сообщения
    :param bot: бот
    :param state: FSMContext
    :param source_type: "general_queue" или "zodiac"
    :param sign: название знака (если zodiac)
    :param queue_index: индекс очереди (если general_queue)
    """
    # Определим описание источника
    if source_type == "zodiac":
        if not sign:
            await message.answer("Ошибка: не указан знак зодиака.")
            return
        path = bot.file_system.get_path(sign, kind="detailed")
        filename = os.path.basename(path) if path else "—"
        date = bot.file_system.get_upload_date(sign, kind="detailed") or "—"
        label = f"[{sign}] Подробный гороскоп"
        state_data = {"file_source_type": "zodiac", "zodiac_sign": sign}
        download_callback = "download_file_zodiac"
        replace_callback = "replace_file_zodiac"

    elif source_type == "general_queue":
        if queue_index is None:
            await message.answer("Ошибка: не указан индекс файла очереди.")
            return
        path = bot.file_system.get_path("general_queue", kind=queue_index)
        filename = os.path.basename(path) if path else "—"
        date = bot.file_system.get_upload_date("general_queue", kind=queue_index) or "—"
        label = f"Файл №{queue_index + 1} из очереди общего гороскопа"
        state_data = {"file_source_type": "general_queue", "queue_index": queue_index}
        download_callback = f"download_general_queue_{queue_index}"
        replace_callback = f"replace_general_queue_{queue_index}"

    else:
        await message.answer("Ошибка: неизвестный тип источника файла.")
        return

    # Сохраняем данные в состояние
    await state.set_state(Admin.file_options)
    await state.update_data(**state_data)

    # Формируем текст
    text = (
        f"<b>{label}</b>\n"
        f"Файл: <code>{filename}</code>\n"
        f"Дата загрузки: {date}"
    )

    # Кнопки
    buttons = {
        "📥 Скачать": download_callback,
        "♻ Заменить": replace_callback,
        "⬅️ Назад": "back_btn"
    }

    await message.answer(
        text=text,
        reply_markup=kb.get_callback_btns(btns=buttons, sizes=(2, 1)),
        parse_mode="HTML"
    )


@admin_router.callback_query(StateFilter(Admin.file_options), F.data.startswith("download_"))
async def download_file(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    file_source_type = data.get("file_source_type")

    if file_source_type == "zodiac":
        zodiac_sign = data.get("zodiac_sign")
        file = bot.file_system.get_file(sign=zodiac_sign, kind="detailed")
        label = f"Файл для {zodiac_sign}"

    elif file_source_type == "general_queue":
        queue_index = data.get("queue_index")
        file = bot.file_system.get_file(sign="general_queue", kind=queue_index)
        label = f"Файл №{queue_index + 1} из очереди"

    else:
        await callback.message.answer("Ошибка: неизвестный источник файла.")
        return

    if not file:
        await callback.message.answer("Файл не найден.")
        return

    await callback.message.delete()
    await bot.send_document(chat_id=callback.message.chat.id, document=file, caption=label)
    await display_file_options(callback.message, bot, state, file_source_type, zodiac_sign if file_source_type == "zodiac" else None, queue_index if file_source_type == "general_queue" else None)
    await callback.answer()



@admin_router.callback_query(StateFilter(Admin.file_options), F.data.startswith("replace_"))
async def replace_file(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    file_source_type = data.get("file_source_type")

    await state.set_state(Admin.upload_file)

    if file_source_type == "zodiac":
        zodiac_sign = data.get("zodiac_sign")
        await callback.message.edit_text(
            text=f"[{zodiac_sign}] Заменить подробный гороскоп.\nОтправьте новый документ:",
            reply_markup=kb.get_callback_btns(btns={
                'Назад': 'back_btn'
            })
        )

    elif file_source_type == "general_queue":
        queue_index = data.get("queue_index")
        await callback.message.edit_text(
            text=f"Заменить файл №{queue_index + 1} из очереди.\nОтправьте новый документ:",
            reply_markup=kb.get_callback_btns(btns={
                'Назад': 'back_btn'
            })
        )

    else:
        await callback.message.answer("Ошибка: неизвестный источник файла.")
        return

    await callback.answer()


@admin_router.callback_query(StateFilter(Admin.file_options), F.data == "back_btn")
async def back_from_file_options(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.message.delete()
    data = await state.get_data()
    file_source_type = data.get("file_source_type")

    if file_source_type == "general_queue":
        # Назад в меню очереди
        await display_general_queue_menu_msg(callback.message, bot, state)
    else:
        # Назад в меню файлов знака зодиака
        zodiac_sign = data.get("zodiac_sign")
        if zodiac_sign:
            await display_zodiac_signs(message=callback.message, state=state)
    await callback.answer()


@admin_router.callback_query(StateFilter(Admin.general_queue_menu), F.data == "back_btn")
async def back_from_general_queue(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Admin.zodiac_sign)

    zodiac_btns = {"Общий гороскоп": "general_queue"}
    zodiac_btns.update(ZODIAC_BTNS)
    zodiac_btns['Назад'] = 'back_btn'

    await callback.message.edit_text(
        "Выбери знак зодиака:",
        reply_markup=kb.get_callback_btns(btns=zodiac_btns, sizes=(1, 2, 2, 2, 2, 2, 2, 1))
    )
    await callback.answer()


@admin_router.callback_query(StateFilter(Admin.upload_file), F.data == "back_btn")
async def back_from_upload_file(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    file_source_type = data.get("file_source_type")
    zodiac_sign = data.get("zodiac_sign")
    queue_index = data.get("queue_index")

    await callback.message.delete()

    # Возврат в меню работы с файлом
    if file_source_type == "zodiac_sign":
        await display_file_options(
            message=callback.message,
            bot=bot,
            state=state,
            source_type=file_source_type,
            sign=zodiac_sign
        )
    elif file_source_type == "general_queue":
        await display_file_options(
            message=callback.message,
            bot=bot,
            state=state,
            source_type=file_source_type,
            queue_index = queue_index
        )

    await callback.answer()


#
# # Кнопка назад из просмотра файлов — возврат к списку знаков
# @admin_router.callback_query(StateFilter(Admin.both_file_options), F.data == 'back_btn')
# async def back_from_files(callback: CallbackQuery, state: FSMContext):
#     await state.set_state(Admin.zodiac_sign)
#     zodiac_btns = ZODIAC_BTNS.copy()
#     zodiac_btns['Назад'] = 'back_btn'
#     await callback.message.edit_text("Выбери знак зодиака:", reply_markup=kb.get_callback_btns(btns=zodiac_btns))
#     await callback.answer()
#
#
#Кнопка назад из меню выбора знаков — закрыть сообщение и остаться в панели
@admin_router.callback_query(StateFilter(Admin.zodiac_sign), F.data == 'back_btn')
async def back_from_zodiac_signs(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Admin.start)
    await callback.message.delete()
    await callback.answer()
#
#
# # Список всех файлов
# @admin_router.message(StateFilter("*"), F.text.casefold() == "список файлов")
# async def list_all_files(message: Message, bot: Bot, state: FSMContext):
#     lines = ["<b>📁 Список файлов по знакам зодиака:</b>"]
#     for sign in ZODIAC_SIGNS:
#         def short(p): return p.split(os.sep)[-1] if p else "—"
#         gen_path = short(bot.file_system.get_path(sign, kind="general"))
#         gen_date = bot.file_system.get_upload_date(sign, kind="general") or "—"
#         det_path = short(bot.file_system.get_path(sign, kind="detailed"))
#         det_date = bot.file_system.get_upload_date(sign, kind="detailed") or "—"
#         lines.append(f"\n<b>{sign}</b>\nОбычный: {gen_path} ({gen_date})\nПодробный: {det_path} ({det_date})")
#
#     await message.answer("\n".join(lines), parse_mode="HTML")



"""
Запуск процесса изменения цены на товары
Для всех товаров установлена единая цена
Выводит текущую цену и дальнейшие варианты взаимодействия
"""
@admin_router.message(StateFilter("*"), F.text.casefold() == "изменить цену")
async def display_price_options(message: Message, bot: Bot, state: FSMContext):
    current_price = bot.price

    await state.clear()
    await state.set_state(Admin.price_options)
    await message.answer(text=f"Текущая цена <b>[{current_price} ⭐️]</b>",
                         reply_markup=kb.get_callback_btns(btns={
                             'Заменить': 'change_price',
                             'Назад': 'back_btn'
                         }))

"""
Раздел работы с рассылкой
Возвращает информацию о текущем состоянии рассылки и предлагает варанты взаимодействия
"""
# Запуск панели управления рассылкой
@admin_router.message(StateFilter("*"), F.text.casefold() == "управлять рассылкой")
async def show_broadcast_menu_entry(message: Message, state: FSMContext, bot: Bot):
    await state.set_state(Admin.broadcast_menu)
    await send_scheduler_status(message=message, bot=bot)


# Универсальный метод для показа статуса рассылки (edit/reply в зависимости от context)
async def send_scheduler_status(message: Message, bot: Bot, edit=False):
    job = bot.scheduler.get_job("daily_forecast_job")
    is_active = job is not None and job.next_run_time is not None

    text = (
        "<b>📬 Статус рассылки</b>\n"
        f"Статус: {'✅ Активна' if is_active else '⛔️ Остановлена'}\n"
        f"Следующий запуск: {job.next_run_time.strftime('%H:%M %d.%m') if is_active else '–'}"
    )
    buttons = {
        "Изменить время": "edit_time",
        ("Остановить" if is_active else "Запустить"): ("pause" if is_active else "resume"),
        "Назад": "back_btn"
    }

    if edit:
        await message.edit_text(text=text, reply_markup=kb.get_callback_btns(btns=buttons))
    else:
        await message.answer(text=text, reply_markup=kb.get_callback_btns(btns=buttons))


# Обработка pause/resume в рамках одного сообщения
@admin_router.callback_query(StateFilter(Admin.broadcast_menu), F.data.in_(["pause", "resume"]))
async def toggle_scheduler(callback: CallbackQuery, bot: Bot, state: FSMContext):
    job = bot.scheduler.get_job("daily_forecast_job")

    if callback.data == "pause" and job:
        job.pause()
        await callback.answer("⛔️ Рассылка остановлена.")
    elif callback.data == "resume" and job:
        job.resume()
        await callback.answer("▶️ Рассылка запущена.")
    else:
        await callback.answer("Операция недоступна.")

    await send_scheduler_status(message=callback.message, bot=bot, edit=True)


# Обработка кнопки "Изменить время"
@admin_router.callback_query(StateFilter(Admin.broadcast_menu), F.data == "edit_time")
async def ask_new_time(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Admin.broadcast_edit_time)
    await callback.answer()
    await callback.message.edit_text(
        text="Введите новое время рассылки в формате <b>ЧЧ:ММ</b>, например <code>10:30</code>",
        reply_markup=kb.get_callback_btns(btns={"Назад": "back_btn"})
    )


# Обработка ввода нового времени
@admin_router.message(StateFilter(Admin.broadcast_edit_time))
async def set_new_time(message: Message, bot: Bot, state: FSMContext):
    import re

    time_pattern = re.fullmatch(r"(\d{1,2}):(\d{2})", message.text.strip())
    if not time_pattern:
        await message.answer("⛔️ Неверный формат. Введите <b>ЧЧ:ММ</b>")
        return

    hour, minute = map(int, time_pattern.groups())
    if not (0 <= hour < 24 and 0 <= minute < 60):
        await message.answer("⛔️ Неверное время. Часы 0–23, минуты 0–59.")
        return

    update_scheduler_time(bot.scheduler, hour, minute)
    await state.set_state(Admin.broadcast_menu)

    # Вместо нового сообщения — ищем последнее и меняем
    last = await message.answer(f"✅ Время обновлено: <b>{hour:02}:{minute:02}</b>")
    await asyncio.sleep(2.5)
    await last.delete()
    await send_scheduler_status(message=message, bot=bot, edit=False)


"""
Закрыть паналь администартора. Состояние Admin обнуляется, клавиатура удаляется
Для повторного включения необходимо ввести команду /start
"""
@admin_router.message(StateFilter("*"), F.text.casefold() == "закрыть панель администратора")
async def close_admin_panel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(text='Панель администратора закрыта', reply_markup=ReplyKeyboardRemove())






""" [change price] Начало работы со сценарием 'изменение цены' """
"""
Заменяет предыдущее сообщения сценария, выводит текущую цену
Запускает ожидаения новой цены
"""
@admin_router.callback_query(StateFilter(Admin.price_options), F.data == 'change_price')
async def request_price(callback: CallbackQuery, bot: Bot, state: FSMContext):
    current_price = bot.price

    await state.set_state(Admin.request_price)
    await callback.answer('')
    await callback.message.edit_text(text=f"Текущая цена <b>[{current_price} ⭐️]</b> \n\n"
                                          f"Отправьте в чат новую цену (в звездах)",
                                     reply_markup=kb.get_callback_btns(btns={
        'Назад': 'back_btn'
    }))


""" 
Ожидает новую цену в формате целое положительное число
После прохождения валидации обновляет цену в bot.price
"""
@admin_router.message(StateFilter(Admin.request_price))
async def change_price(message: Message, bot: Bot, state: FSMContext):
    try:
        new_price = int(message.text)
        if new_price <= 0:
            raise ValueError("Цена должна быть положительным числом.")
        #telegram ожидает цену в копейках
        bot.price = new_price

        await state.clear()
        await state.set_state(Admin.start)
        await message.answer(text=f"Новая цена успешно установлена: {bot.price} ⭐️")

    except ValueError as e:
        await message.answer(text=f"Ошибка: {e}. Пожалуйста, введите положительное целое число.")




""" Позволяет вернуть звезды тг при тестировании бота """
@admin_router.message(Command('back'))
async def refund(message: Message, bot: Bot, command:CommandObject):
    await bot.refund_star_payment(user_id=message.chat.id, telegram_payment_charge_id=command.args)





""" [Back_button] Кнопка назад в различных сценариях"""

""" Кнопка назад для выхода из работы с файлами """




""" Кнопка назад при изменении цены. Завершает сценарий "выбор цены" оставляет сообщение с текущей ценой """
@admin_router.callback_query(StateFilter(Admin.price_options, Admin.request_price), F.data == 'back_btn')
async def back_step_change_price(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    current_price = bot.price
    await state.clear()
    await state.set_state(Admin.start)
    await callback.answer(text='')
    await callback.message.edit_text(text=f"Текущая цена <b>[{current_price}]</b>")


@admin_router.callback_query(StateFilter(Admin.broadcast_menu), F.data == "back_btn")
async def back_from_broadcast(callback: CallbackQuery, state: FSMContext):
    await admin_cmd(callback.message, state)
    await callback.answer()


@admin_router.callback_query(StateFilter(Admin.broadcast_edit_time), F.data == "back_btn")
async def back_to_broadcast_menu(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await state.set_state(Admin.broadcast_menu)
    await callback.answer()
    await send_scheduler_status(message=callback.message, bot=bot, edit=True)

