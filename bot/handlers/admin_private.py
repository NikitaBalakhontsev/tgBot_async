import os
import pathlib
import traceback

from aiogram import F, Router, Bot
from aiogram.filters import Command, StateFilter, or_f
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from aiogram.types import FSInputFile
from aiogram.utils.formatting import as_list, as_marked_section

import bot.keyboards as kb
from bot.filters import ChatTypeFilter, IsAdmin

admin_router = Router()
admin_router.message.filter(ChatTypeFilter(["private"]), IsAdmin())


class Admin(StatesGroup):
    start = State()
    zodiac_sign = State()
    upload_file = State()
    price_options = State()
    request_price = State()
    filename = 'none'


def update_files_dict(files_dict: dict, data_path: pathlib.Path):
    for zodiac_sign in files_dict.keys():
        path = pathlib.Path(f'{data_path}/{zodiac_sign}.pdf')
        if path.exists():
            print(f'файл {zodiac_sign} найден, путь {path}')
            files_dict[zodiac_sign] = path


@admin_router.message(Command("admin"))
async def admin_cmd(message: Message, state: FSMContext ):
    await message.answer(text="Запущена панель администратора", reply_markup=kb.get_reply_btns(
        "Изменить файлы",
        "Список файлов",
        "Изменить цену",
        "Закрыть панель администратора",
        placeholder="Панель администратора",
        sizes=(2, 1, 1)
    ))
    await state.set_state(Admin.start)


@admin_router.message(StateFilter(Admin.start), F.text.casefold() == "изменить файлы")
async def display_zodiac_signs(message: Message, bot: Bot, state: FSMContext):
    update_files_dict(files_dict=bot.files_dict, data_path=bot.data_path)
    zodiac_btns = {sign['ru']: sign['ru'] for sign in bot.zodiac_signs}
    await message.answer(text='Выбери знак зодиака', reply_markup=kb.get_callback_btns(btns=zodiac_btns))
    await state.set_state(Admin.start)

@admin_router.message(StateFilter(Admin.start), F.text.casefold() == "список файлов")
async def display_files(message: Message, bot: Bot):
    update_files_dict(files_dict=bot.files_dict, data_path=bot.data_path)

    data_path = bot.data_path
    if not os.path.exists(data_path):
        await message.answer(text=f'Директория {data_path} не найдено. Проверьте значение параметра bot.data_path в файле app.py')
        return
    files = os.listdir(data_path)
    zodiac_files = bot.files_dict.values()

    used_files = [filename for filename in files if pathlib.Path(data_path, filename) in zodiac_files]
    unused_files = [filename for filename in files if filename not in used_files]

    used_files_section = as_marked_section("Используемые файлы", *used_files, marker='✅')
    unused_files_section = as_marked_section("Неиспользуемые файлы", *unused_files, marker='❌')
    files_list = as_list(used_files_section, unused_files_section, sep='\n')
    await message.answer(text=files_list.as_html())


@admin_router.message(StateFilter(Admin.start), F.text.casefold() == "изменить цену")
async def display_price_options(message: Message, bot: Bot, state: FSMContext):
    current_price = bot.price
    await message.answer(text= f'Текущая цена <b>[{current_price}]</b>',
                        reply_markup=kb.get_callback_btns(btns={
                            'Заменить': 'change_price',
                            'Назад': 'back_btn'
                        }))
    await state.set_state(Admin.price_options)


@admin_router.message(StateFilter("*"), F.text.casefold() == "закрыть панель администратора")
async def close_admin_panel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(text='Панель администратора закрыта', reply_markup=ReplyKeyboardRemove())


#[change price]

@admin_router.callback_query(StateFilter(Admin.price_options), F.data =='change_price')
async def request_price(callback: CallbackQuery, bot: Bot, state: FSMContext):
    current_price = bot.price
    await callback.answer('')
    await callback.message.edit_text(text=f'Текущая цена <b>[{current_price}]</b> \n\n Отправьте в чат новую цену ('
                                          f'целое,в рублях)', reply_markup=kb.get_callback_btns(btns={
        'Назад': 'back_btn'
    }))
    await state.set_state(Admin.request_price)


@admin_router.message(StateFilter(Admin.request_price))
async def change_price(message: Message, bot:Bot, state: FSMContext):
    try:
        new_price = int(message.text)
        if new_price <= 0:
            raise ValueError("Цена должна быть положительным числом.")

        bot.price = new_price
        await message.answer(text=f"Новая цена успешно установлена: {new_price}")
        await state.clear()
        await state.set_state(Admin.start)

    except ValueError as e:
        await message.answer(text=f"Ошибка: {e}. Пожалуйста, введите положительное целое число.")

#[/change_price]

@admin_router.callback_query(StateFilter(Admin.start), F.data.in_(
    {'Овен', 'Телец', 'Близнецы', 'Рак', 'Лев', 'Дева', 'Весы', 'Скорпион', 'Стрелец',
     'Козерог', 'Водолей', 'Рыбы'}))
async def display_file_options(callback: CallbackQuery, bot: Bot, state: FSMContext):
    await state.set_state(Admin.zodiac_sign)

    if callback.data == 'back_btn':
        state_data = await state.get_data()
        zodiac_sign = state_data['zodiac_sign']
    else:
        zodiac_sign = callback.data

    filename = bot.files_dict[zodiac_sign]
    await state.update_data(zodiac_sign=zodiac_sign, filename=filename)

    await callback.answer(text='')
    if filename == 'none':
        await callback.message.edit_text(text=f'[{zodiac_sign}] Файл: <b> {filename} </b>',
                                         reply_markup=kb.get_callback_btns(btns={
                                             'Заменить': 'upload',
                                             'Назад': 'back_btn'
                                         }))
    else:
        await callback.message.edit_text(text=f'[{zodiac_sign}] Файл: <b> {filename} </b>',
                                         reply_markup=kb.get_callback_btns(btns={
                                             'Скачать': 'download',
                                             'Заменить': 'upload',
                                             'Назад': 'back_btn'
                                         }))


@admin_router.callback_query(StateFilter(Admin.zodiac_sign), F.data == 'upload')
async def send_file_by_name(callback: CallbackQuery, bot: Bot, state: FSMContext):
    state_data = await state.get_data()
    zodiac_sign = state_data['zodiac_sign']
    await callback.answer('')
    await callback.message.edit_text(
        text=f'[{zodiac_sign}] Заменить файл:<b> {zodiac_sign}.pdf </b> \n\n Отправьте в чат новый файл',
        reply_markup=kb.get_callback_btns(btns={
            'Назад': 'back_btn'
        }))
    await state.set_state(Admin.upload_file)


@admin_router.message(StateFilter(Admin.upload_file), F.document)
async def doc_save(message: Message, state: FSMContext, bot: Bot):
    try:
        state_data = await state.get_data()
        zodiac_sign = state_data['zodiac_sign']

        file_id = message.document.file_id
        file = await bot.get_file(file_id)
        file_path = file.file_path

        new_filename = f'{zodiac_sign}.pdf'
        destination_directory = bot.data_path
        destination = destination_directory / new_filename  # Создаем полный путь к новому файлу

        if destination.exists():
            # Если файл существует, удаляем его
            destination.unlink()

        await bot.download_file(file_path=file_path, destination=destination)
        bot.files_dict[zodiac_sign]
        await state.set_state('zodiac_sign')
    except Exception as e:
        await message.reply(text=f'Ошибка загрузки файла: {e}, error: {traceback.format_exc()}')
    await message.reply(text=f'Файл {new_filename} успешно добавлен')
    await state.clear()
    await state.set_state(Admin.start)


@admin_router.callback_query(F.data == 'download')
async def send_file_by_name(callback: CallbackQuery, bot: Bot, state: FSMContext):
    state_data = await state.get_data()
    zodiac_sign = state_data['zodiac_sign']
    path = bot.files_dict[zodiac_sign]
    file = FSInputFile(path)

    await callback.answer(f'файл {path} отправлен')
    await callback.message.answer_document(document=file)


@admin_router.callback_query(StateFilter(Admin.zodiac_sign), F.data == 'back_btn')
async def back_step_zodiac_sign(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    await state.clear()
    await state.set_state(Admin.start)
    update_files_dict(files_dict=bot.files_dict, data_path=bot.data_path)
    zodiac_btns = {sign['ru']: sign['ru'] for sign in bot.zodiac_signs}

    await callback.answer(text='')
    await callback.message.edit_text(text='Выбери знак зодиака',
                                     reply_markup=kb.get_callback_btns(btns=zodiac_btns))


@admin_router.callback_query(StateFilter(Admin.upload_file), F.data == 'back_btn')
async def back_step_upload(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    await state.set_state(Admin.zodiac_sign)
    await callback.answer(text='')
    await display_file_options(callback=callback, bot=bot, state=state)

@admin_router.callback_query(StateFilter(Admin.price_options, Admin.request_price), F.data == 'back_btn')
async def back_step_upload(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    current_price = bot.price
    await state.clear()
    await callback.answer(text='')
    await callback.message.edit_text(text=f'Текущая цена <b>[{current_price}]</b>')
    await state.set_state(Admin.start)

'''
@admin_router.callback_query(F.data == 'back_btn')
async def back_step_upload(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    await state.clear()
    await callback.answer(text='')
    await display_zodiac_signs(message=callback.message, bot=bot, state=state)
'''