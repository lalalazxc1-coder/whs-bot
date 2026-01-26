from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import FSInputFile
import openpyxl
import os
from datetime import datetime

import config
import database.requests as db
from states import AdminPanelState

router = Router()

def get_admin_main_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="📢 Рассылка объявлений", callback_data="admin_broadcast")
    builder.button(text="⬇️ Отчеты Excel", callback_data="admin_reports_menu")
    builder.button(text="📞 Управление контактами", callback_data="admin_contacts")
    builder.adjust(1)
    return builder.as_markup()

def get_admin_reports_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 За 7 дней", callback_data="admin_export_7")
    builder.button(text="📅 За 30 дней", callback_data="admin_export_30")
    builder.button(text="♾ За все время", callback_data="admin_export_0")
    builder.button(text="⬅️ Назад", callback_data="admin_cancel")
    builder.adjust(1)
    return builder.as_markup()

@router.message(Command("admin"))
async def cmd_admin_panel(message: types.Message):
    if message.from_user.id not in config.ADMIN_IDS:
        return
    await message.answer("🛠 **Панель Администратора**", reply_markup=get_admin_main_kb(), parse_mode="Markdown")

# --- Рассылка ---

@router.callback_query(F.data == "admin_broadcast")
async def broadcast_start(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in config.ADMIN_IDS: return
    
    # Выбор цели: Все или Филиал
    builder = InlineKeyboardBuilder()
    builder.button(text="🌍 Всем", callback_data="broadcast_target_all")
    
    branches = await db.get_branches()
    for b in branches:
        builder.button(text=f"🏢 {b.name}", callback_data=f"broadcast_target_branch_{b.id}")
        
    builder.button(text="❌ Отмена", callback_data="admin_cancel")
    builder.adjust(2)
    
    await callback.message.edit_text("📢 **Рассылка:** Кому отправить сообщение?", reply_markup=builder.as_markup())
    await state.set_state(AdminPanelState.select_target)

@router.callback_query(AdminPanelState.select_target, F.data.startswith("broadcast_target_"))
async def broadcast_enter_msg(callback: types.CallbackQuery, state: FSMContext):
    target = callback.data.split("_")[2] # all or branch
    branch_id = None
    if target == "branch":
        branch_id = int(callback.data.split("_")[3])
        
    await state.update_data(target=target, branch_id=branch_id)
    
    await callback.message.edit_text("✍️ Введите текст объявления (можно с фото):")
    await state.set_state(AdminPanelState.broadcast_msg)

@router.message(AdminPanelState.broadcast_msg)
async def broadcast_send(message: types.Message, state: FSMContext):
    data = await state.get_data()
    target = data.get("target")
    branch_id = data.get("branch_id")
    
    # Получаем пользователей
    if target == "all":
        users = await db.get_all_users()
    else:
        users = await db.get_users_by_branch(branch_id)
        
    if not users:
        await message.answer("Пользователи не найдены.")
        await state.clear()
        return
    
    count = 0
    # Отправка
    notify_msg = await message.answer(f"⏳ Начинаю рассылку для {len(users)} пользователей...")
    
    for u in users:
        try:
            await message.copy_to(u.telegram_id)
            count += 1
        except Exception:
            pass # Юзер заблочил бота
            
    await notify_msg.edit_text(f"✅ Рассылка завершена!\nДоставлено: {count} из {len(users)}")
    await state.clear()

@router.callback_query(F.data == "admin_cancel")
async def admin_cancel(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Отменено.", reply_markup=get_admin_main_kb())

# --- Экспорт ---

@router.callback_query(F.data == "admin_reports_menu")
async def export_menu_handler(callback: types.CallbackQuery):
    await callback.message.edit_text("📊 **Выберите период отчета:**", reply_markup=get_admin_reports_kb())

@router.callback_query(F.data.startswith("admin_export_"))
async def export_data_handler(callback: types.CallbackQuery):
    if callback.from_user.id not in config.ADMIN_IDS: return
    
    days = int(callback.data.split("_")[2]) # 7, 30, 0
    period_name = f"{days} дней" if days > 0 else "Все время"
    
    await callback.message.answer(f"⏳ Генерирую отчет ({period_name})...")
    
    reports = await db.get_reports_by_range(days)
    all_tickets = await db.get_tickets_by_range(days)
    
    # Разделяем тикеты на Обычные и Заказы
    # Сначала убираем заказы
    non_orders = [t for t in all_tickets if not t.message.startswith("[ЗАКАЗ МАТЕРИАЛОВ]")]
    orders = [t for t in all_tickets if t.message.startswith("[ЗАКАЗ МАТЕРИАЛОВ]")]
    
    # Теперь разделяем non_orders на Проблемы и Вопросы
    problems = [t for t in non_orders if t.ticket_type == 'problem']
    questions = [t for t in non_orders if t.ticket_type == 'question']
    # Для совместимости старых записей (где ticket_type может быть не заполнен, но дефолт 'problem')
    # можно считать problem по умолчанию. Но так как мы уже добавили колонку с дефолтом, все ок.
    
    wb = openpyxl.Workbook()
    
    # --- Лист 1: Инвентаризация ---
    ws1 = wb.active
    ws1.title = "Inventory"
    ws1.append(["ID", "Date", "Branch", "User", "Report Data"])
    
    for r in reports:
        # User Link Formula
        user_display = r.user_name if r.user_name else str(r.user_id)
        user_link_formula = f'=HYPERLINK("tg://user?id={r.user_id}", "{user_display}")'
        
        ws1.append([r.id, r.timestamp, r.branch_name, user_link_formula, r.report_data])

    # --- Лист 2: Проблемы (Problems) ---
    ws2 = wb.create_sheet("Problems")
    ws2.append(["ID", "Date", "Status", "Branch", "Sender", "Message", "Responder", "Reply", "Reply Date"])
    
    for t in problems:
        # Sender Link
        sender_display = t.user_name if t.user_name else str(t.user_id)
        sender_link = f'=HYPERLINK("tg://user?id={t.user_id}", "{sender_display}")'
        
        # Responder Link
        if t.responder_id:
            responder_display = t.responder_name if t.responder_name else str(t.responder_id)
            responder_link = f'=HYPERLINK("tg://user?id={t.responder_id}", "{responder_display}")'
        else:
            responder_link = ""

        ws2.append([
            t.id, t.created_at, t.status, t.branch_name, 
            sender_link, t.message, 
            responder_link, t.reply_message, t.reply_at
        ])

    # --- Лист 3: Вопросы (Questions) ---
    ws_q = wb.create_sheet("Questions")
    ws_q.append(["ID", "Date", "Status", "Branch", "Sender", "Message", "Responder", "Reply", "Reply Date"])
    
    for t in questions:
        # Sender Link
        sender_display = t.user_name if t.user_name else str(t.user_id)
        sender_link = f'=HYPERLINK("tg://user?id={t.user_id}", "{sender_display}")'
        
        # Responder Link
        if t.responder_id:
            responder_display = t.responder_name if t.responder_name else str(t.responder_id)
            responder_link = f'=HYPERLINK("tg://user?id={t.responder_id}", "{responder_display}")'
        else:
            responder_link = ""

        ws_q.append([
            t.id, t.created_at, t.status, t.branch_name, 
            sender_link, t.message, 
            responder_link, t.reply_message, t.reply_at
        ])
        
    # --- Лист 3: Заявки (Orders) ---
    ws3 = wb.create_sheet("Orders")
    ws3.append(["ID", "Date", "Status", "Branch", "User", "Order Details", "Responder", "Note"])
    
    for o in orders:
        # Убираем префикс [ЗАКАЗ МАТЕРИАЛОВ] для красоты
        clean_msg = o.message.replace("[ЗАКАЗ МАТЕРИАЛОВ]", "").strip()
        
        user_display = o.user_name if o.user_name else str(o.user_id)
        user_link = f'=HYPERLINK("tg://user?id={o.user_id}", "{user_display}")'
        
        responder_link = ""
        if o.responder_id:
             responder_display = o.responder_name if o.responder_name else str(o.responder_id)
             responder_link = f'=HYPERLINK("tg://user?id={o.responder_id}", "{responder_display}")'
             
        ws3.append([
            o.id, o.created_at, o.status, o.branch_name,
            user_link, clean_msg,
            responder_link, o.reply_message
        ])
        
    # Сохраняем
    filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    wb.save(filename)
    
    # Отправляем
    try:
        file = FSInputFile(filename)
        await callback.message.answer_document(file, caption=f"📊 Отчет ({period_name})")
    finally:
        if os.path.exists(filename):
            os.remove(filename)

    await callback.answer()

# --- Управление контактами (UI) ---

@router.callback_query(F.data == "admin_contacts")
async def admin_contacts_list(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in config.ADMIN_IDS: return

    contacts = await db.get_contacts()
    
    builder = InlineKeyboardBuilder()
    
    # Список контактов с кнопкой удаления
    text = "📞 **Список контактов:**\n\n"
    if not contacts:
        text += "Контактов нет."
    
    for c in contacts:
        text += f"🔹 {c.department} | {c.info}\n"
        builder.button(text=f"🗑 Удалить: {c.department[:10]}...", callback_data=f"admin_del_contact_{c.id}")
        
    builder.button(text="➕ Добавить контакт", callback_data="admin_add_contact")
    builder.button(text="⬅️ Назад", callback_data="admin_cancel")
    builder.adjust(1)
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")

@router.callback_query(F.data == "admin_add_contact")
async def admin_add_contact_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("✍️ Введите название отдела (например: Логистика):")
    await state.set_state(AdminPanelState.contact_dept)

@router.message(AdminPanelState.contact_dept)
async def admin_add_contact_dept(message: types.Message, state: FSMContext):
    await state.update_data(contact_dept=message.text)
    await message.answer("✍️ Введите данные контакта(ов).\nФормат: Имя - Телефон - Почта\n\nМожно несколько строк.")
    await state.set_state(AdminPanelState.contact_info)

@router.message(AdminPanelState.contact_info)
async def admin_add_contact_save(message: types.Message, state: FSMContext):
    data = await state.get_data()
    dept = data.get("contact_dept")
    info = message.text
    
    await db.add_contact(dept, info)
    
    await message.answer(f"✅ Контакт добавлен: {dept} - {info}")
    
    # Возвращаемся в меню контактов (эмуляция)
    # Так как мы отправили новое сообщение, лучше отправить новое меню
    await message.answer("🛠 **Панель Администратора**", reply_markup=get_admin_main_kb(), parse_mode="Markdown")
    await state.clear()

@router.callback_query(F.data.startswith("admin_del_contact_"))
async def admin_del_contact(callback: types.CallbackQuery):
    cid = int(callback.data.split("_")[3])
    if await db.delete_contact(cid):
        await callback.answer("✅ Контакт удален")
        # Обновим список
        await admin_contacts_list(callback, None) 
    else:
        await callback.answer("❌ Ошибка при удалении", show_alert=True)
