from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from utils.locales import get_text

def main_menu(lang="ru"):
    kb = [
        [KeyboardButton(text=get_text(lang, "btn_feedback")), KeyboardButton(text=get_text(lang, "btn_question"))],
        [KeyboardButton(text=get_text(lang, "btn_inventory")), KeyboardButton(text=get_text(lang, "btn_order"))],
        [KeyboardButton(text=get_text(lang, "btn_contacts"))],
        [KeyboardButton(text=get_text(lang, "btn_settings"))]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def select_sector_kb():
    kb = [
        [KeyboardButton(text="🛢 OIL (Масла)"), KeyboardButton(text="🔧 AP (Запчасти)")],
        [KeyboardButton(text="🏢 Весь склад (OIL + AP)")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
