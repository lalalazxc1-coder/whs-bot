from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from utils.locales import get_text

def main_menu(lang="ru"):
    kb = [
        [KeyboardButton(text=get_text(lang, "btn_inventory"))],
        [KeyboardButton(text=get_text(lang, "btn_feedback")), KeyboardButton(text=get_text(lang, "btn_question"))],
        [KeyboardButton(text=get_text(lang, "btn_order"))],
        [KeyboardButton(text=get_text(lang, "btn_settings")), KeyboardButton(text=get_text(lang, "btn_contacts"))]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
