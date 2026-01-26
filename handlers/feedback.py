from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

import config
import keyboards.reply as kb_reply
import database.requests as db
from states import FeedbackState
from utils.locales import get_text

router = Router()

@router.message(F.text.in_({"⚠️ Сообщить о проблеме", "⚠️ Мәселе туралы хабарлау", "❓ Задать вопрос", "❓ Сұрақ қою"}))
async def feedback_start(message: types.Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    lang = user.language
    
    # Определяем тип тикета по тексту кнопки
    if message.text in ["❓ Задать вопрос", "❓ Сұрақ қою"]:
        ticket_type = "question"
        prompt = get_text(lang, "question_ask")
    else:
        ticket_type = "problem"
        prompt = get_text(lang, "feedback_ask")
        
    await state.update_data(ticket_type=ticket_type)
    await message.answer(prompt, reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(FeedbackState.write_message)

@router.message(FeedbackState.write_message)
async def feedback_send(message: types.Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    lang = user.language if user else "ru"
    branch_name = user.branch.name if user and user.branch else "---"

    data = await state.get_data()
    ticket_type = data.get("ticket_type", "problem")
    
    # Создаем тикет в БД
    message_content = message.text or message.caption or "[Media]"
    ticket_id = await db.create_ticket(
        user_id=message.from_user.id,
        user_name=message.from_user.full_name,
        branch_name=branch_name,
        message=message_content,
        ticket_type=ticket_type
    )

    if ticket_type == "question":
        header_template = get_text(lang, "question_header")
        target_group = config.QUESTIONS_GROUP_ID
    else:
        header_template = get_text(lang, "feedback_header")
        target_group = config.SUPPORT_GROUP_ID

    header = header_template.format(branch=branch_name, user=f"{message.from_user.full_name} (ID: {message.from_user.id})")
    header += f"\n🔢 Ticket ID: #{ticket_id}"

    if not target_group:
        await message.answer("Error: Target group not configured.")
        await state.clear()
        return

    builder = InlineKeyboardBuilder()
    # Теперь в кнопке передаем ID тикета
    builder.button(text=get_text(lang, "feedback_reply_btn"), callback_data=f"reply_ticket_{ticket_id}")
    
    try:
        await message.bot.send_message(target_group, header, parse_mode="Markdown")
        await message.copy_to(target_group, reply_markup=builder.as_markup())
        await message.answer(get_text(lang, "feedback_sent"), reply_markup=kb_reply.main_menu(lang))
    except Exception as e:
        print(f"Error sending feedback: {e}")
        await message.answer("Error sending message.")
            
    await state.clear()
