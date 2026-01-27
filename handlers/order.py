from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
import asyncio
import config
import database.requests as db
import keyboards.reply as kb_reply
from states import OrderState
from utils.locales import get_text

router = Router()

def get_items_keyboard(items, lang, cart=None):
    if cart is None:
        cart = {}
    cart_size = len(cart)
    
    builder = InlineKeyboardBuilder()
    
    # Кнопка Готово (если корзина не пуста, можно выделить)
    label_done = f"{get_text(lang, 'order_done_btn')} ({cart_size})" if cart_size > 0 else get_text(lang, 'order_done_btn')
    builder.button(text=label_done, callback_data="order_done")
    
    # Кнопка Отмена
    builder.button(text=get_text(lang, 'order_cancel_btn'), callback_data="order_cancel")
    
    # Товары
    for item in items:
        qty = cart.get(item.name)
        if qty:
            btn_text = f"✅ {item.name} ({qty})"
        else:
            btn_text = item.name
            
        builder.button(text=btn_text, callback_data=f"order_item_{item.id}")
        
    builder.adjust(2) # Готово/Отмена вверху, затем товары
    return builder.as_markup()

@router.message(F.text.in_({"📦 Заказ материалов", "📦 Материалдарға тапсырыс"}))
async def order_start(message: types.Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    lang = user.language if user else "ru"
    
    if not user.selected_branch_id:
        await message.answer(get_text(lang, "inventory_start_err_branch"))
        return

    # Головной офис check
    if user.branch and user.branch.name == "Головной офис":
        msg = "Сізге материалдарға тапсырыс беру қажет емес." if lang == "kz" else "Вам не нужно заказывать материалы."
        await message.answer(msg)
        return

    items = await db.get_active_items()
    if not items:
        await message.answer(get_text(lang, "inventory_start_err_empty"))
        return
    
    # Инициализируем корзину
    await state.update_data(cart={}, lang=lang, branch_id=user.selected_branch_id)
    
    kb = get_items_keyboard(items, lang, cart={})
    await message.answer(get_text(lang, "order_choose_item"), reply_markup=kb)
    await state.set_state(OrderState.choose_item)

@router.callback_query(OrderState.choose_item, F.data.startswith("order_item_"))
async def order_item_click(callback: types.CallbackQuery, state: FSMContext):
    item_id = int(callback.data.split("_")[2])
    data = await state.get_data()
    lang = data.get("lang", "ru")
    
    # Ищем название товара (лучше бы закэшировать, но для небольшого списка сойдет)
    items = await db.get_active_items() 
    item_name = next((i.name for i in items if i.id == item_id), "Item")
    
    # Сохраняем ID сообщения меню, чтобы потом к нему вернуться или удалить
    await state.update_data(current_item_id=item_id, current_item_name=item_name, menu_msg_id=callback.message.message_id)
    
    text = get_text(lang, "order_enter_qty").format(item=item_name)
    # Редактируем текущее сообщение (вместо присылки нового)
    await callback.message.edit_text(text, reply_markup=None) 
    # (Кнопки убираем, ждем ввод. Можно добавить кнопку "Отмена" инлайном, но пока так)
    
    await state.set_state(OrderState.enter_qty)
    await callback.answer()

@router.message(OrderState.enter_qty)
async def order_enter_qty(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    menu_msg_id = data.get("menu_msg_id")

    # Удаляем сообщение пользователя с цифрой (для чистоты)
    try:
        await message.delete()
    except:
        pass # Если нет прав на удаление
    
    if not message.text.isdigit():
        # Если ошибка - отправляем временное сообщение и удаляем через 2 сек (чтобы не мусорить)
        msg = await message.answer(get_text(lang, "error_digit"))
        await asyncio.sleep(2)
        await msg.delete()
        return
        
    qty = int(message.text)
    cart = data.get("cart", {})
    item_name = data.get("current_item_name")
    
    cart[item_name] = qty
    await state.update_data(cart=cart)
    
    # Возвращаемся к выбору: Редактируем то самое сообщение, которое сейчас спрашивает "Введите количество"
    # Но так как мы удалили сообщение юзера, у нас нет объекта message для edit_text старого сообщения,
    # но мы знаем menu_msg_id. Используем bot.edit_message_text
    
    items = await db.get_active_items()
    kb = get_items_keyboard(items, lang, cart)
    
    added_text = get_text(lang, "order_added").format(item=item_name, qty=qty)
    full_text = f"{added_text}\n\n{get_text(lang, 'order_choose_item')}"
    
    try:
        await message.bot.edit_message_text(
            text=full_text,
            chat_id=message.chat.id,
            message_id=menu_msg_id,
            reply_markup=kb
        )
    except Exception as e:
        # Если вдруг не вышло (сообщение слишком старое), шлем новое
        await message.answer(full_text, reply_markup=kb)
    
    await state.set_state(OrderState.choose_item)

@router.callback_query(OrderState.choose_item, F.data == "order_cancel")
async def order_cancel(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    await callback.message.edit_text("❌")
    await callback.message.answer("Menu", reply_markup=kb_reply.main_menu(lang))
    await state.clear()

@router.callback_query(OrderState.choose_item, F.data == "order_done")
async def order_done(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("lang", "ru")
    cart = data.get("cart", {})
    
    if not cart:
        await callback.answer(get_text(lang, "order_empty"), show_alert=True)
        return
        
    # Формируем заказ
    branch = await db.get_branch_by_id(data['branch_id'])
    branch_name = branch.name if branch else "Unknown"
    
    items_str = "\n".join([f"▫️ {k}: {v} шт." for k, v in cart.items()])
    
    header_template = get_text(lang, "order_header")
    order_text = header_template.format(branch=branch_name, user=callback.from_user.full_name, items=items_str)
    
    # Создаем Тикет в БД (чтобы админы могли ответить "Принято в работу")
    ticket_id = await db.create_ticket(
        user_id=callback.from_user.id,
        user_name=callback.from_user.full_name,
        branch_name=branch_name,
        message="[ЗАКАЗ МАТЕРИАЛОВ]\n" + items_str
    )
    
    # Отправляем в группу
    if config.SUPPORT_GROUP_ID:
        builder = InlineKeyboardBuilder()
        builder.button(text=f"Ответить #{ticket_id}", callback_data=f"reply_ticket_{ticket_id}")
        
        await callback.bot.send_message(
            config.SUPPORT_GROUP_ID, 
            order_text + f"\n\n🔢 Ticket ID: #{ticket_id}", 
            reply_markup=builder.as_markup(),
            parse_mode="Markdown"
        )
    
    await callback.message.edit_text(get_text(lang, "order_sent"))
    # Возврат в меню (хотя мы не убирали Reply клаву, так что она там)
    await state.clear()
