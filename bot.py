import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ContentType
from aiogram.types import Message, LabeledPrice, PreCheckoutQuery, FSInputFile
from aiogram.filters import Command

import config
from config import TOKEN
from bot.handlers import router



bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(F.text, Command('payment'))
async def payment(message: Message):
    await bot.send_invoice(message.chat.id,
                           'Прогноз',
                           'Ты узнаешь все',
                           'invoice',
                           config.PAYMENT_TOKEN,
                           'RUB',
                           [LabeledPrice(label='Прогноз', amount= 200 * 100)]
                           )

@dp.pre_checkout_query(lambda query: True)
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@dp.message(F.successful_payment)
async def successful_payment(message:Message):
    for j,k in message.successful_payment:
        print(f"{j} = {k}")
    await message.answer(f'Ваш платеж на сумму {message.successful_payment.total_amount // 100} прошел успешно. Ниже прикреплен файл с разбором' )
    await message.answer_document(FSInputFile(path=r'C:\Users\Nikita\PycharmProjects\tg_bot_test\data\test.pdf'))

async def main():
    dp.include_router(router=router)
    await dp.start_polling(bot, skip_updates=False)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Exit by keyboard')
