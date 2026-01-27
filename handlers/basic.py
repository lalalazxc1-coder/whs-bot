from aiogram import Router, F, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

import database.requests as db
import keyboards.reply as kb_reply
import keyboards.inline as kb_inline
from utils.locales import get_text

import config

router = Router()

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    user_id = message.from_user.id
    
    text = (
        "📚 **Справка / Көмек:**\n\n"
        "🔹 `/start` - Перезапуск бота / Ботты қайта қосу\n"
        "🔹 `📦 Отправить остатки` - Сдать отчет по инвентаризации\n"
        "🔹 `📦 Заказ материалов` - Заказать расходники\n"
        "🔹 `📞 Контакты` - Номера телефонов отделов\n"
        "🔹 `⚙️ Настройки` - Смена языка, филиала и сектора\n"
        "🔹 `⚠️ Сообщить о проблеме` - Написать о проблеме\n"
        "🔹 `❓ Задать вопрос` - Задать вопрос по логистике\n"
    )
    
    if user_id in config.ADMIN_IDS:
        text += (
            "\n👮‍♂️ **Admin Help:**\n"
            "🔸 `/admin` - **Главное меню администратора**\n"
            "   (Отчеты, Авто-расписание, Контакты, Филиалы, Товары, Тикеты)\n\n"
            "🔸 **/remind <Text>** - Рассылка напоминания (устар. лучше через меню)\n"
            "   Настройте авто-открытие в меню `/admin` -> Авто-расписание.\n"
            "   Или открывайте вручную.\n\n"
            "🔸 **Тикеты и Заказы (Группы):**\n"
            "   Отвечайте на них прямо из меню `/admin` кнопкой 'Ответить'.\n"
            "   Так же можно отвечать в Группах Поддержки, нажав кнопку под сообщением."
        )
        
    await message.answer(text, parse_mode="Markdown")

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    user = await db.add_user(user_id)
    
    # Если пользователь уже настроен (выбрал филиал), сразу открываем меню
    if user.selected_branch_id:
        lang = user.language
        text = get_text(lang, "welcome_registered").format(user_name=message.from_user.full_name)
        await message.answer(text, reply_markup=kb_reply.main_menu(lang), parse_mode="Markdown")
        return

    # Если новый пользователь - начинаем с выбора языка
    # Используем дефолтный (ru) текст приветствия, так как язык еще не выбран, 
    # но можно вывести на обоих языках, если бы ключ не был в словаре.
    # Так как мы не знаем язык, возьмем 'ru' как базу для приветствия, или сделаем комбинированный текст вручную, но у нас в словаре уже разные тексты.
    # Давайте просто выведем Текст RU + Текст KZ.
    
    user_name = message.from_user.full_name
    welcome_text = get_text("ru", "start_welcome").format(user_name=user_name) + "\n\n" + get_text("kz", "start_welcome").format(user_name=user_name)
    
    await message.answer(
        welcome_text,
        reply_markup=kb_inline.language_selection()
    )

@router.callback_query(F.data.startswith("lang_"))
async def cb_language_select(callback: types.CallbackQuery):
    lang_code = callback.data.split("_")[1]
    await db.update_user_language(callback.from_user.id, lang_code)
    
    text = get_text(lang_code, "lang_selected")
    await callback.message.answer(text)
    
    # Теперь проверяем филиал
    user = await db.get_user(callback.from_user.id)
    if not user.selected_branch_id:
        branches = await db.get_branches()
        if not branches:
            await callback.message.answer("No branches found.")
        else:
            await callback.message.answer(get_text(lang_code, "select_branch"), reply_markup=kb_inline.branches_list(branches))
    else:
        await callback.message.answer(get_text(lang_code, "menu_main"), reply_markup=kb_reply.main_menu(lang_code))
    
    await callback.answer()

from states import RegistrationState

@router.callback_query(F.data.startswith("branch_"))
async def cb_branch_select(callback: types.CallbackQuery, state: FSMContext):
    branch_id = int(callback.data.split("_")[1])
    await db.update_user_branch(callback.from_user.id, branch_id)
    
    user = await db.get_user(callback.from_user.id)
    lang = user.language if user else "ru"
    
    # Если Головной офис - пропускаем выбор сектора
    if user.branch and user.branch.name == "Головной офис":
        await db.update_user_sector(callback.from_user.id, "full")
        await callback.message.answer(get_text(lang, "branch_saved"), reply_markup=kb_reply.main_menu(lang))
        await state.clear()
        await callback.answer()
        return

    # Теперь спрашиваем сектор
    await callback.message.answer(
        "Выберите ваш сектор / Секторды таңдаңыз:", 
        reply_markup=kb_reply.select_sector_kb()
    )
    await state.set_state(RegistrationState.select_sector)
    await callback.answer()

@router.message(RegistrationState.select_sector)
async def cb_sector_select(message: types.Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    lang = user.language if user else "ru"
    
    # Определяем код сектора по тексту
    text = message.text
    sector_code = "full"
    if "OIL" in text and "AP" not in text:
        sector_code = "oil"
    elif "AP" in text and "OIL" not in text:
        sector_code = "ap"
    # иначе full (Весь склад)
    
    await db.update_user_sector(message.from_user.id, sector_code)
    
    await message.answer(get_text(lang, "branch_saved"), reply_markup=kb_reply.main_menu(lang))
    await state.clear()

# --- Настройки ---

@router.message(F.text.in_({"⚙️ Настройки", "⚙️ Баптаулар"}))
async def cmd_settings(message: types.Message):
    user = await db.get_user(message.from_user.id)
    lang = user.language
    branch_name = user.branch.name if user.branch else "---"
    
    text = get_text(lang, "current_settings").format(lang=lang.upper(), branch=branch_name)
    await message.answer(text, reply_markup=kb_inline.settings_menu(lang))

@router.callback_query(F.data == "settings_lang")
async def cb_settings_lang(callback: types.CallbackQuery):
    await callback.message.answer("Выберите язык / Тілді таңдаңыз:", reply_markup=kb_inline.language_selection())
    await callback.answer()

@router.callback_query(F.data == "settings_branch")
async def cb_settings_branch(callback: types.CallbackQuery):
    branches = await db.get_branches()
    user = await db.get_user(callback.from_user.id)
    lang = user.language
    await callback.message.answer(get_text(lang, "select_branch"), reply_markup=kb_inline.branches_list(branches))
    await callback.answer()

@router.message(F.text.in_({"📞 Контакты отделов", "📞 Бөлімдер байланысы"}))
async def cmd_contacts(message: types.Message):
    user = await db.get_user(message.from_user.id)
    lang = user.language if user else "ru"
    
    contacts = await db.get_contacts()
    
    if not contacts:
        await message.answer("Контакты еще не добавлены.", parse_mode="Markdown")
        return

    # Группируем по отделам
    grouped = {}
    for c in contacts:
        if c.department not in grouped:
            grouped[c.department] = []
        grouped[c.department].append(c.info)
    
    # Формируем текст
    header = "📞 **Контакты отделов / Контактілер:**\n\n"
    body = ""
    
    for dept, infos in grouped.items():
        body += f"🏢 **{dept}:**\n"
        for info in infos:
            body += f"{info}\n"
        body += "\n"
        
    await message.answer(header + body, parse_mode="Markdown")
