from aiogram import types

async def main_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = ["Создать заявку", "Мои заявки", "Курсы", "Поддержка"]
    keyboard.add(*buttons)
    return keyboard
