"""Точка входа Telegram-бота."""
import asyncio
import logging

from aiogram import Dispatcher

from app.core.db import create_db, init_engine
from app.core.loader import create_bot, create_dispatcher
from app.core.modules import ModuleRegistry
from app.core.security import AccessMiddleware, ContextInjectorMiddleware, RateLimitMiddleware
from config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    settings = get_settings()

    init_engine(settings.database_url)
    await create_db()

    bot = create_bot(settings.bot_token)
    dispatcher: Dispatcher = create_dispatcher()

    registry = ModuleRegistry(dispatcher, settings)
    registry.load_modules()

    dispatcher.message.middleware(AccessMiddleware(settings.allowed_users))
    dispatcher.message.middleware(RateLimitMiddleware(settings.rate_limit_per_user_per_minute))
    dispatcher.message.middleware(ContextInjectorMiddleware(settings, registry))

    try:
        logger.info("Бот запущен. Ожидаем обновления...")
        await dispatcher.start_polling(bot)
    finally:
        logger.info("Остановка бота...")


if __name__ == "__main__":
    asyncio.run(main())
