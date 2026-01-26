from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, StateFilter
from aiogram.utils.keyboard import InlineKeyboardBuilder

import config
import database.requests as db
from states import AdminReplyState

router = Router()

# --- Просмотр списка тикетов ---
@router.message(Command("tickets"))
async def cmd_tickets_list(message: types.Message):
    # Доступ только из группы или админам
    allowed_chats = [config.SUPPORT_GROUP_ID, config.QUESTIONS_GROUP_ID]
    if message.chat.id not in allowed_chats and message.from_user.id not in config.ADMIN_IDS:
        return

    tickets = await db.get_open_tickets()
    if not tickets:
        await message.reply("🎉 Нет открытых заявок!")
        return

    text = f"📨 **Открытые заявки ({len(tickets)}):**\n\n"
    
    for t in tickets:
        # Обрезаем текст для превью
        preview = t.message[:50] + "..." if len(t.message) > 50 else t.message
        text += f"🔹 **#{t.id}** | {t.user_name} ({t.branch_name})\n📝 {preview}\n\n"
        
    text += "✍️ **Чтобы ответить, отправьте ID тикета (цифрами) в этот чат.**"
    await message.reply(text, parse_mode="Markdown")

# --- Ответ на тикет ---

# --- Ответ на тикет (ввод ID) ---

@router.message(F.text.regexp(r"^\d+$"), StateFilter(None))
async def ticket_id_reply_start(message: types.Message, state: FSMContext):
    # Доступ только из группы или админам
    allowed_chats = [config.SUPPORT_GROUP_ID, config.QUESTIONS_GROUP_ID]
    if message.chat.id not in allowed_chats and message.from_user.id not in config.ADMIN_IDS:
        return

    try:
        ticket_id = int(message.text)
    except ValueError:
        return

    ticket = await db.get_ticket(ticket_id)
    if not ticket:
        # Не отвечаем, если тикета нет, чтобы не спамить на любые цифры
        return
    
    if ticket.status == "closed":
        await message.reply(f"⚠️ Тикет #{ticket_id} уже закрыт.")
        return 
    
    await state.update_data(ticket_id=ticket.id, reply_to_user_id=ticket.user_id)
    await state.set_state(AdminReplyState.write_reply)
    
    await message.reply(
        f"✍️ Введите ответ для заявки **#{ticket.id}**\n"
        f"От: {ticket.user_name}\n"
        f"Текст: {ticket.message}",
        parse_mode="Markdown"
    )

@router.message(AdminReplyState.write_reply)
async def send_reply_to_user(message: types.Message, state: FSMContext):
    data = await state.get_data()
    target_user_id = data.get("reply_to_user_id")
    ticket_id = data.get("ticket_id")
    
    if not target_user_id or not ticket_id:
        await message.reply("Ошибка контекста. Попробуйте нажать кнопку Ответить снова.")
        await state.clear()
        return

    try:
        # Отправляем сообщение пользователю
        await message.bot.send_message(
            target_user_id,
            f"Менеджер {message.from_user.full_name} ответил на вашу заявку #{ticket_id}:\n{message.text}",
            parse_mode="Markdown"
        )
        
        # Закрываем тикет в БД и сохраняем ответ
        await db.close_ticket(
            ticket_id, 
            message.text, 
            responder_id=message.from_user.id, 
            responder_name=message.from_user.full_name
        )
        
        await message.reply(f"✅ Ответ отправлен. Тикет #{ticket_id} закрыт.")
    except Exception as e:
        await message.reply(f"❌ Не удалось отправить: {e}")
    
    await state.clear()

# --- Отчеты ---
@router.message(Command("report"))
async def cmd_report_group(message: types.Message):
    if message.chat.id != config.SUPPORT_GROUP_ID and message.from_user.id not in config.ADMIN_IDS:
        return

    reports = await db.get_last_reports(limit=5)
    if not reports:
        await message.reply("Нет свежих отчетов.")
        return

    text = "📊 **Последние 5 отчетов:**\n\n"
    for r in reports:
        text += (
            f"📅 {r.timestamp.strftime('%Y-%m-%d %H:%M')}\n"
            f"📍 {r.branch_name} (User: {r.user_id})\n"
            f"📝 {r.report_data}\n"
            f"-------------------\n"
        )
    await message.reply(text)
