"""Точка входа Telegram-бота."""
import asyncio
import logging

from aiogram import Dispatcher

from app.core.db import create_db, init_engine
from app.core.loader import create_bot, create_dispatcher

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




if __name__ == "__main__":
    asyncio.run(main())
