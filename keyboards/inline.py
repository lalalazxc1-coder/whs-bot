from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from utils.locales import get_text

def branches_list(branches):
    builder = InlineKeyboardBuilder()
    for branch in branches:
        builder.button(text=branch.name, callback_data=f"branch_{branch.id}")
    builder.adjust(2)
    return builder.as_markup()

def language_selection():
    kb = [
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton(text="🇰🇿 Қазақша", callback_data="lang_kz")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def settings_menu(lang="ru"):
    kb = [
        [InlineKeyboardButton(text=get_text(lang, "btn_change_lang"), callback_data="settings_lang")],
        [InlineKeyboardButton(text=get_text(lang, "btn_change_branch"), callback_data="settings_branch")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)
