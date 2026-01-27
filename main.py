import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

import config
from database.models import init_db
from handlers import basic, inventory, feedback, admin, admin_group, order, admin_panel
from utils import scheduler

async def main():
    # Инициализация БД
    await init_db()

    bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # Подключаем роутеры модулей
    dp.include_routers(
        admin.router,
        admin_group.router,
        admin_panel.router,
        basic.router,
        inventory.router,
        order.router,
        feedback.router
    )

    logging.basicConfig(level=logging.INFO)
    
    # Запуск планировщика
    scheduler.start_scheduler(bot)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
