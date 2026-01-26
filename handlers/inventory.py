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
    user = await db.get_user(message.from_user.id)
    lang = user.language

    if not user.selected_branch_id:
        await message.answer(get_text(lang, "inventory_start_err_branch"))
        return

    items = await db.get_active_items()
    if not items:
        await message.answer(get_text(lang, "inventory_start_err_empty"))
        return

    items_data = [{"id": i.id, "name": i.name} for i in items]
    await state.update_data(items=items_data, current_index=0, report={}, branch_id=user.selected_branch_id, lang=lang)
    
    first_item = items_data[0]
    
    # Инструкция перед началом
    await message.answer(get_text(lang, "inventory_intro"), reply_markup=types.ReplyKeyboardRemove())
    
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
        
        summary = "\n".join([f"{k}: {v}" for k, v in report.items()])
        full_report = f"📊 REPORT\nBranch: {branch_name}\n\n{summary}"
        
        await db.save_report(message.from_user.id, branch_name, summary, user_name=message.from_user.full_name)
        
        for admin_id in config.ADMIN_IDS:
            try:
                await message.bot.send_message(admin_id, f"New Report from {message.from_user.full_name}:\n{full_report}")
            except:
                pass
        
        # Если есть группа поддержки, можно туда тоже кинуть отчет, но пока оставим только админам в ЛС и БД
        
        await message.answer(get_text(lang, "report_accepted"), reply_markup=kb_reply.main_menu(lang))
        await state.clear()
