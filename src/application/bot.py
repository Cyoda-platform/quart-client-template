# Основной файл запуска
import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher import filters
from aiogram.utils import executor

# Настройки логирования
logging.basicConfig(level=logging.INFO)

# Получаем токен из переменных окружения
API_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# Основные команды
@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    await message.reply("Привет! Я бот для обмена криптовалюты. Используйте меню для навигации.")

# Обработка выбора обмена
@dp.message_handler(filters.Text(equals='Создать заявку'))
async def create_request(message: types.Message):
    await message.reply("Введите сумму для обмена:")

# Получение курса валют (пример интеграции)
async def get_exchange_rate(base_currency, target_currency):
    # Здесь будет ваша логика для получения курса
    # Пример:
    return 5.0  # Возвращаем фиктивный курс

# Основной файл запуска
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)