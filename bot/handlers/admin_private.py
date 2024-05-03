import json
import os
import traceback

from pathlib import Path
from aiogram import F, Router, Bot
from aiogram.filters import Command, StateFilter, or_f
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from aiogram.types import FSInputFile
from aiogram.utils.formatting import as_list, as_marked_section

import bot.keyboards as kb
from bot.filters import ChatTypeFilter, IsAdmin

# Используем отдельный роутер для управления диалогом с администратором.
# Список администраторов хранится в bot.admin_list в формате user_id
admin_router = Router()
admin_router.message.filter(ChatTypeFilter(["private"]), IsAdmin())


# Состояния для работы администратора
class Admin(StatesGroup):
    start = State()
    zodiac_sign = State()
    file_options = State()
    upload_file = State()

    price_options = State()
    request_price = State()

    filename = 'none'


# Считываем данные из директории data путь храниться в bot.data_path
def update_files_dict(files_dict: dict, data_path: Path):
    for zodiac_sign in files_dict.keys():
        path = Path(f'{data_path}/{zodiac_sign}.pdf')
        if path.exists():
            #print(f'файл {zodiac_sign} найден, путь {path}')
            files_dict[zodiac_sign]['path'] = str(path)


# Запуск панели администратора
@admin_router.message(Command("admin"))
async def admin_cmd(message: Message, state: FSMContext):
    await message.answer(text="Запущена панель администратора", reply_markup=kb.get_reply_btns(
        "Изменить файлы",
        "Список файлов",
        "Изменить цену",
        "Закрыть панель администратора",
        placeholder="Панель администратора",
        sizes=(2, 1, 1)
    ))
    await state.set_state(Admin.start)


# Запуск процесса работы с файлами
# Знак зодиака хранит путь к файлу .pdf
# Выводит знаки зодиака и ожидает от пользователя выбор знака
@admin_router.message(StateFilter("*"), F.text.casefold() == "изменить файлы")
async def display_zodiac_signs(message: Message, bot: Bot, state: FSMContext):
    update_files_dict(files_dict=bot.files_dict, data_path=bot.data_path)
    zodiac_btns = {sign['ru']: sign['ru'] for sign in bot.zodiac_signs}
    zodiac_btns['Назад'] = 'back_btn'
    await message.answer(text='Выбери знак зодиака', reply_markup=kb.get_callback_btns(btns=zodiac_btns))

    await state.clear()
    await state.set_state(Admin.zodiac_sign)


# Выводит на экран все файлы, найденные в директории data
# Файлы разделены на категории: используемые и неиспользуемые
# Используемые закреплены за знаком зодиака и являются товаром
@admin_router.message(StateFilter("*"), F.text.casefold() == "список файлов")
async def display_files(message: Message, bot: Bot, state: FSMContext):
    update_files_dict(files_dict=bot.files_dict, data_path=bot.data_path)

    data_path = bot.data_path
    if not os.path.exists(data_path):
        await message.answer(
            text=f'Директория {data_path} не найдено. Проверьте значение параметра bot.data_path в файле app.py')
        return
    files = os.listdir(data_path)
    zodiac_paths = [data['path'] for data in bot.files_dict.values() if data['path'] is not None]

    used_files = [filename for filename in files if str(Path(data_path, filename)) in zodiac_paths]
    unused_files = [filename for filename in files if filename not in used_files]

    used_files_section = as_marked_section("Используемые файлы", *used_files, marker='✅')
    unused_files_section = as_marked_section("Неиспользуемые файлы", *unused_files, marker='❌')
    files_list = as_list(used_files_section, unused_files_section, sep='\n')

    await state.clear()
    await state.set_state(Admin.start)
    await message.answer(text=files_list.as_html())


# Запуск процесса изменения цены на товары
# Для всех товаров установлена единая цена
# Выводит текущую цену и дальнейшие варианты взаимодействия
@admin_router.message(StateFilter("*"), F.text.casefold() == "изменить цену")
async def display_price_options(message: Message, bot: Bot, state: FSMContext):
    current_price = bot.price

    await state.clear()
    await state.set_state(Admin.price_options)
    await message.answer(text=f'Текущая цена <b>[{current_price // 100}]</b>',
                         reply_markup=kb.get_callback_btns(btns={
                             'Заменить': 'change_price',
                             'Назад': 'back_btn'
                         }))



# Закрыть паналь администартора. Состояние Admin обнуляется, клавиатура удаляется
# Для повторного включения необходимо ввести команду /start
@admin_router.message(StateFilter("*"), F.text.casefold() == "закрыть панель администратора")
async def close_admin_panel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(text='Панель администратора закрыта', reply_markup=ReplyKeyboardRemove())


# [change price] Начало работы со сценарием "изменение цены"

# Заменяет предыдущее сообщения сценария, выводит текущую цену
# Запускает ожидаения новой цены
@admin_router.callback_query(StateFilter(Admin.price_options), F.data == 'change_price')
async def request_price(callback: CallbackQuery, bot: Bot, state: FSMContext):
    current_price = bot.price

    await state.set_state(Admin.request_price)
    await callback.answer('')
    await callback.message.edit_text(text=f'Текущая цена <b>[{current_price // 100}]</b> \n\n Отправьте в чат новую цену ('
                                          f'целое,в рублях)', reply_markup=kb.get_callback_btns(btns={
        'Назад': 'back_btn'
    }))



# Ожидает новую цену в формате целое положительное число
# После прохождения валидации обновляет цену в bot.price
@admin_router.message(StateFilter(Admin.request_price))
async def change_price(message: Message, bot: Bot, state: FSMContext):
    try:
        new_price = int(message.text)
        if new_price <= 0:
            raise ValueError("Цена должна быть положительным числом.")
        #telegram ожидает цену в копейках
        bot.price = new_price * 100

        await state.clear()
        await state.set_state(Admin.start)
        await message.answer(text=f"Новая цена успешно установлена: {bot.price // 100}")

    except ValueError as e:
        await message.answer(text=f"Ошибка: {e}. Пожалуйста, введите положительное целое число.")


# [Change_file] Начало работы со сценарием "изменение файлов"

# Ожидает знак зодиака в формате CallbackQuery либо кнопку назад
# Выводит текущий знак зодиака и прикрепленный к нему файл
# Выводит возможные действия с файлом
# Если файл не найден выведет none без возможности скачать файл
@admin_router.callback_query(StateFilter(Admin.zodiac_sign), F.data.in_(
    {'Овен', 'Телец', 'Близнецы', 'Рак', 'Лев', 'Дева', 'Весы', 'Скорпион', 'Стрелец',
     'Козерог', 'Водолей', 'Рыбы'}))
async def display_file_options(callback: CallbackQuery, bot: Bot, state: FSMContext):
    await state.set_state(Admin.zodiac_sign)

    if callback.data == 'back_btn':
        state_data = await state.get_data()
        zodiac_sign = state_data['zodiac_sign']
    else:
        zodiac_sign = callback.data

    filename = bot.files_dict[zodiac_sign]['path']

    if filename == 'none':
        keyboard = kb.get_callback_btns(btns={
            'Заменить': 'upload',
            'Назад': 'back_btn'
        })
    else:
        keyboard = kb.get_callback_btns(btns={
            'Скачать': 'download',
            'Заменить': 'upload',
            'Назад': 'back_btn'
        })

    await state.update_data(zodiac_sign=zodiac_sign, filename=filename)
    await state.set_state(Admin.file_options)
    await callback.answer(text='')
    await callback.message.edit_text(text=f'[{zodiac_sign}] Файл: <b> {filename} </b>',
                                     reply_markup=keyboard)


# Запускает процесс загрузки нового файла
# Выводит текущий знак зодиака и прикрепленный к нему файл
# Запускает ожидание документа
@admin_router.callback_query(StateFilter(Admin.file_options), F.data == 'upload')
async def request_new_file(callback: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    zodiac_sign = state_data['zodiac_sign']

    await state.set_state(Admin.upload_file)
    await callback.answer('')
    await callback.message.edit_text(
        text=f'[{zodiac_sign}] Заменить файл:<b> {zodiac_sign}.pdf </b> \n\n Отправьте в чат новый файл',
        reply_markup=kb.get_callback_btns(btns={
            'Назад': 'back_btn'
        }))



# Ожидает документ
# Закрепляет за знаком зодиака, предварительно меняя название файла
# Удаляет ранее прикрепленный документ
@admin_router.message(StateFilter(Admin.upload_file), F.document)
async def doc_save(message: Message, state: FSMContext, bot: Bot):
    try:
        state_data = await state.get_data()
        zodiac_sign = state_data['zodiac_sign']

        file_id = message.document.file_id
        file = await bot.get_file(file_id)
        file_path = file.file_path

        new_filename = f'{zodiac_sign}.pdf'
        destination = Path(bot.data_path, new_filename)  # Создаем полный путь к новому файлу

        if destination.exists():
            destination.unlink()

        await bot.download_file(file_path=file_path, destination=destination)
        bot.files_dict[zodiac_sign]['path'] = str(destination)
        bot.files_dict[zodiac_sign]['id'] = file_id

        json_path = Path(bot.data_path, 'files.json')
        with open(json_path, 'w') as file:
            json.dump(bot.files_dict, file, indent=4,  ensure_ascii=False)

    except Exception as e:
        await message.reply(text=f'Ошибка загрузки файла: {e}, error: {traceback.format_exc()}')

    await state.clear()
    await state.set_state(Admin.start)
    await message.reply(text=f'Файл {new_filename} успешно добавлен')

# Отправляет документ, прикрепленный за выбранным знаком зодиака
@admin_router.callback_query(F.data == 'download')
async def send_file_by_name(callback: CallbackQuery, bot: Bot, state: FSMContext):
    state_data = await state.get_data()
    zodiac_sign = state_data['zodiac_sign']
    file_id = bot.files_dict[zodiac_sign]['id']
    file_path = bot.files_dict[zodiac_sign]['path']

    if file_id:
        await callback.answer(f'файл {file_path} отправлен по id')
        await callback.message.answer_document(document=file_id)
    else:
        file = FSInputFile(file_path)
        await callback.answer(f'файл {file_path} отправлен')
        await callback.message.answer_document(document=file)


# [/Change_file]

# [Back_button] Кнопка назад в различных сценариях

#Кнопка назад для выхода из работы с файлами
@admin_router.callback_query(StateFilter(Admin.zodiac_sign), F.data == 'back_btn')
async def back_step_files(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    await state.clear()
    await state.set_state(Admin.start)
    await callback.answer(text='')
    await callback.message.edit_text(text=f'Изменение файлов <b>[Отмена]</b>')

# Кнопка назад после выбора знака зодиака. Запускает выбор знака зодиака заново.
@admin_router.callback_query(StateFilter(Admin.file_options), F.data == 'back_btn')
async def back_step_file_options(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    update_files_dict(files_dict=bot.files_dict, data_path=bot.data_path)
    zodiac_btns = {sign['ru']: sign['ru'] for sign in bot.zodiac_signs}
    zodiac_btns['Назад'] = 'back_btn'

    await state.clear()
    await state.set_state(Admin.zodiac_sign)
    await callback.answer(text='')
    await callback.message.edit_text(text='Выбери знак зодиака',
                                     reply_markup=kb.get_callback_btns(btns=zodiac_btns))


# Кнопка назад при замене файла. Запускает выбор действий с файлов заново
@admin_router.callback_query(StateFilter(Admin.upload_file), F.data == 'back_btn')
async def back_step_upload(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    await state.set_state(Admin.zodiac_sign)
    await callback.answer(text='')
    await display_file_options(callback=callback, bot=bot, state=state)


# Кнопка назад при изменении цены. Завершает сценарий "выбор цены" оставляет сообщение с текущей ценой
@admin_router.callback_query(StateFilter(Admin.price_options, Admin.request_price), F.data == 'back_btn')
async def back_step_change_price(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    current_price = bot.price
    await state.clear()
    await state.set_state(Admin.start)
    await callback.answer(text='')
    await callback.message.edit_text(text=f'Текущая цена <b>[{current_price}]</b>')

# [/Back_button]
