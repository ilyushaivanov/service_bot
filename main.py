import asyncio
import logging

from aiogram import Bot, Dispatcher

from config import BOT_TOKEN
from database import Database
from handlers.admin_handlers import router as admin_router
from handlers.user_handlers import router as user_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Основная функция для запуска бота."""
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    db = Database()

    @dp.update.outer_middleware()
    async def database_middleware(handler, event, data):
        data['db'] = db
        return await handler(event, data)

    dp.include_router(user_router)
    dp.include_router(admin_router)

    logger.info("✅ Бот запущен!")
    logger.info("Команды: /start, /anketa, /template, /admin")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
