from aiogram import Dispatcher
from aiogram import types

async def register_handlers(dp: Dispatcher):
    dp.register_message_handler(send_welcome, commands=['start', 'help'])
    dp.register_message_handler(create_request, text='Создать заявку')

# Обработчик для получения курса валют
async def get_exchange_rate(base_currency, target_currency):
    # Логика получения курса
    return 5.0
