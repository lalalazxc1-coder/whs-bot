from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext

import database.requests as db
import keyboards.reply as kb_reply
import config
from states import InventoryState
from utils.locales import get_text

router = Router()

@router.message(F.text.in_({"📦 Отправить остатки", "📦 Қалдықтарды жіберу"}))
async def start_inventory(message: types.Message, state: FSMContext):
    await start_inventory_logic(message, state, message.from_user.id)

@router.callback_query(F.data == "start_inventory")
async def start_inventory_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await start_inventory_logic(callback.message, state, callback.from_user.id)

async def start_inventory_logic(message: types.Message, state: FSMContext, user_id: int):
    user = await db.get_user(user_id)
    lang = user.language

    if not user.selected_branch_id:
        await message.answer(get_text(lang, "inventory_start_err_branch"))
        return

    # Головной офис check
    if user.branch and user.branch.name == config.HEAD_OFFICE_NAME:
        msg = get_text(lang, "inventory_head_office_deny")
        await message.answer(msg)
        return


    # Проверяем, открыта ли инвентаризация
    # Проверяем, открыта ли инвентаризация
    if not await db.is_inventory_open():
        await message.answer(get_text(lang, "inventory_closed_warning"))
        return

    items = await db.get_active_items()
    if not items:
        await message.answer(get_text(lang, "inventory_start_err_empty"))
        return

    # Пока нет разделения товаров по типам в БД, спрашиваем все товары для всех.
    # Но сохраняем отчет с пометкой сектора пользователя.
    
    items_data = [{"id": i.id, "name": i.name} for i in items]
    
    # Сохраняем сектор в состояние, чтобы потом передать в save_report
    user_sector = user.sector if user.sector else config.SECTOR_FULL

    await state.update_data(
        items=items_data, 
        current_index=0, 
        report={}, 
        branch_id=user.selected_branch_id, 
        lang=lang,
        user_sector=user_sector
    )
    
    first_item = items_data[0]
    
    # Инструкция перед началом
    # Инструкция перед началом
    sector_name = user_sector.upper()
    await message.answer(f"{get_text(lang, 'inventory_intro')}\n\n{get_text(lang, 'inventory_intro_sector').format(sector=sector_name)}", reply_markup=types.ReplyKeyboardRemove(), parse_mode="Markdown")
    
    await message.answer(f"{get_text(lang, 'enter_qty')} {first_item['name']}")
    await state.set_state(InventoryState.fill_item)

@router.message(InventoryState.fill_item)
async def process_item_count(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")

    if not message.text.isdigit():
        await message.answer(get_text(lang, "error_digit"))
        return

    count = int(message.text)
    items = data['items']
    idx = data['current_index']
    report = data['report']
    
    current_item_name = items[idx]['name']
    report[current_item_name] = count
    
    next_idx = idx + 1
    if next_idx < len(items):
        await state.update_data(current_index=next_idx, report=report)
        next_item = items[next_idx]['name']
        await message.answer(f"{get_text(lang, 'enter_qty')} {next_item}")
    else:
        branch_id = data['branch_id']
        branch = await db.get_branch_by_id(branch_id)
        branch_name = branch.name if branch else "Unknown"
        user_sector = data.get("user_sector", config.SECTOR_FULL)
        
        summary = "\n".join([f"{k}: {v}" for k, v in report.items()])
        full_report = f"📊 REPORT ({user_sector.upper()})\nBranch: {branch_name}\nUser: {message.from_user.full_name}\n\n{summary}"
        
        # Сохраняем с учетом сектора
        await db.save_report(
            user_id=message.from_user.id, 
            branch_name=branch_name, 
            report_data=summary, 
            user_name=message.from_user.full_name,
            sector=user_sector
        )
        
        # Уведомления админам (опционально, можно убрать чтобы не спамить)
        # for admin_id in config.ADMIN_IDS:
        #     try:
        #         await message.bot.send_message(admin_id, f"New Report:\n{full_report}")
        #     except: pass
        
        await message.answer(get_text(lang, "report_accepted"), reply_markup=kb_reply.main_menu(lang))
        await state.clear()
