from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
import database.requests as db
from utils.locales import get_text
from datetime import datetime

import config

scheduler = AsyncIOScheduler()

async def check_auto_inventory_status(bot: Bot):
    """
    Проверяет, нужно ли автоматически открыть/закрыть инвентаризацию по расписанию.
    """
    # 1. Проверяем, включен ли авто-режим
    auto_mode = await db.get_setting("inventory_auto_mode", "0")
    if auto_mode != "1":
        return

    # 2. Получаем настройки дней
    try:
        start_day = int(await db.get_setting("inventory_start_day", "25"))
        end_day = int(await db.get_setting("inventory_end_day", "1"))
    except:
        return # Ошибка в настройках
        
    current_day = datetime.now().day
    is_open = await db.is_inventory_open()
    
    # 3. Логика открытия
    if current_day == start_day and not is_open:
        await db.set_setting("inventory_open", "1")
        
        # Уведомляем админов
        for admin_id in config.ADMIN_IDS:
             try: await bot.send_message(admin_id, "⚙️ **Авто-планировщик:** Сбор отчетов ОТКРЫТ.")
             except: pass
             
        # Рассылка пользователям
        users = await db.get_all_users()
        for u in users:
            try:
                lang = u.language if u.language else "ru"
                if lang == "kz":
                    msg = "🔔 **Назар аударыңыз!**\n\nҚалдықтарды жинау басталды. Есеп тапсырыңыз."
                else:
                    msg = "🔔 **Внимание!**\n\nОткрыт сбор отчетов по остаткам. Пожалуйста, сдайте отчет."
                await bot.send_message(u.telegram_id, msg)
            except: pass
            
    # 4. Логика закрытия
    elif current_day == end_day and is_open:
        await db.set_setting("inventory_open", "0")
        
        # Уведомляем админов
        for admin_id in config.ADMIN_IDS:
             try: await bot.send_message(admin_id, "⚙️ **Авто-планировщик:** Сбор отчетов ЗАКРЫТ.")
             except: pass

async def send_daily_reminders(bot: Bot):
    """
    Рассылает напоминания пользователям, которые не сдали отчет за последние 24 часа.
    """
    # Только если инвентаризация открыта?
    # Логично, что напоминать нужно только когда сбор открыт.
    if not await db.is_inventory_open():
        return

    users = await db.get_users_pending_report()
    
    if not users:
        return

    for user in users:
        lang = user.language if user.language else "ru"
        
        # Получаем текст напоминания
        header = get_text(lang, "reminder_header")
        body = get_text(lang, "reminder_body").format(date=datetime.now().strftime("%d.%m.%Y"))
        
        message_text = f"{header}\n\n{body}"
        
        try:
            await bot.send_message(user.telegram_id, message_text)
        except Exception as e:
            # Пользователь мог заблокировать бота
            print(f"Failed to send reminder to {user.telegram_id}: {e}")

def start_scheduler(bot: Bot):
    # Запускаем задачу каждый день в 09:00 - Reminder
    scheduler.add_job(send_daily_reminders, 'cron', hour=9, minute=0, args=[bot])
    
    # ПРОВЕРКА АВТО-СТАТУСА:
    # Запускаем, например, в 08:00 утра.
    scheduler.add_job(check_auto_inventory_status, 'cron', hour=8, minute=0, args=[bot])
    
    scheduler.start()
