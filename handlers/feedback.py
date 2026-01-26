from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

import config
import keyboards.reply as kb_reply
import database.requests as db
from states import FeedbackState
from utils.locales import get_text

router = Router()

@router.message(F.text.in_({"⚠️ Сообщить о проблеме", "⚠️ Мәселе туралы хабарлау"}))
async def feedback_start(message: types.Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    lang = user.language
    await message.answer(get_text(lang, "feedback_ask"), reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(FeedbackState.write_message)

@router.message(FeedbackState.write_message)
async def feedback_send(message: types.Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    lang = user.language if user else "ru"
    branch_name = user.branch.name if user and user.branch else "---"

    # Создаем тикет в БД
    message_content = message.text or message.caption or "[Media]"
    ticket_id = await db.create_ticket(
        user_id=message.from_user.id,
        user_name=message.from_user.full_name,
        branch_name=branch_name,
        message=message_content
    )

    header_template = get_text(lang, "feedback_header")
    header = header_template.format(branch=branch_name, user=f"{message.from_user.full_name} (ID: {message.from_user.id})")
    header += f"\n🔢 Ticket ID: #{ticket_id}"

    if not config.SUPPORT_GROUP_ID:
        await message.answer("Error: Support group not configured.")
        await state.clear()
        return

    builder = InlineKeyboardBuilder()
    # Теперь в кнопке передаем ID тикета
    builder.button(text=get_text(lang, "feedback_reply_btn"), callback_data=f"reply_ticket_{ticket_id}")
    
    try:
        await message.bot.send_message(config.SUPPORT_GROUP_ID, header, parse_mode="Markdown")
        await message.copy_to(config.SUPPORT_GROUP_ID, reply_markup=builder.as_markup())
        await message.answer(get_text(lang, "feedback_sent"), reply_markup=kb_reply.main_menu(lang))
    except Exception as e:
        print(f"Error sending feedback: {e}")
        await message.answer("Error sending message.")
            
    await state.clear()
