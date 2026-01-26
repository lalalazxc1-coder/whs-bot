from aiogram import Router, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

import config
import database.requests as db
from utils.locales import get_text

router = Router()

# Фильтр на админа можно написать кастомный или проверять внутри
def is_admin(user_id):
    return user_id in config.ADMIN_IDS

@router.message(Command("add_branch"))
async def add_branch(message: types.Message):
    if not is_admin(message.from_user.id): return
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Пример: /add_branch Название")
        return
        
    try:
        await db.add_branch(args[1])
        await message.answer(f"Филиал {args[1]} создан.")
    except Exception as e:
        await message.answer(f"Ошибка: {e}")

@router.message(Command("add_item"))
async def add_item(message: types.Message):
    if not is_admin(message.from_user.id): return
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Пример: /add_item Товар")
        return

    try:
        await db.add_item(args[1])
        await message.answer(f"Товар {args[1]} создан.")
    except Exception as e:
        await message.answer(f"Ошибка: {e}")

# --- Контакты ---
@router.message(Command("contacts_admin"))
async def cmd_list_contacts(message: types.Message):
    if not is_admin(message.from_user.id): return
    
    contacts = await db.get_contacts()
    if not contacts:
        await message.answer("Контактов нет.")
        return
        
    text = "📋 **Список контактов:**\n\n"
    for c in contacts:
        text += f"ID: `{c.id}` | {c.department} | {c.info}\n"
        
    text += "\nДобавить: `/add_contact Отдел Данные`\nУдалить: `/del_contact ID`"
    await message.answer(text, parse_mode="Markdown")

@router.message(Command("add_contact"))
async def cmd_add_contact(message: types.Message):
    if not is_admin(message.from_user.id): return
    
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("Пример: `/add_contact Логистика Иван 87771234567`", parse_mode="Markdown")
        return
        
    dept = args[1]
    info = args[2]
    
    await db.add_contact(dept, info)
    await message.answer(f"✅ Добавлено: {dept} - {info}")

@router.message(Command("del_contact"))
async def cmd_del_contact(message: types.Message):
    if not is_admin(message.from_user.id): return
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Пример: `/del_contact 1`")
        return
        
    try:
        cid = int(args[1])
        if await db.delete_contact(cid):
            await message.answer(f"✅ Контакт {cid} удален.")
        else:
            await message.answer("❌ Контакт не найден.")
    except ValueError:
        await message.answer("ID должен быть числом.")

@router.message(Command("remind"))
async def cmd_remind_report(message: types.Message):
    """
    Отправляет напоминание всем пользователям о сдаче отчета.
    Использование: /remind 17:00 Пятницы
    """
    if not is_admin(message.from_user.id): return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("⚠️ Укажите дату/время.\nПример: `/remind завтра до 12:00`", parse_mode="Markdown")
        return
        
    deadline_text = args[1]
    users = await db.get_all_users()
    
    if not users:
        await message.answer("Пользователей не найдено.")
        return
        
    await message.answer(f"⏳ Рассылка напоминания для {len(users)} пользователей...")
    
    count = 0
    for u in users:
        lang = u.language
        text = f"{get_text(lang, 'reminder_header')}\n\n{get_text(lang, 'reminder_body').format(date=deadline_text)}"
        
        builder = InlineKeyboardBuilder()
        builder.button(text=get_text(lang, "btn_inventory"), callback_data="start_inventory")
        
        try:
            await message.bot.send_message(u.telegram_id, text, parse_mode="Markdown", reply_markup=builder.as_markup())
            count += 1
        except Exception:
            pass
            
    await message.answer(f"✅ Напоминание отправлено {count} из {len(users)} пользователей.")
