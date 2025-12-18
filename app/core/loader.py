"""Создание экземпляров бота и диспетчера."""
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties


def create_bot(token: str) -> Bot:
    return Bot(token=token, default=DefaultBotProperties(parse_mode="HTML"))


def create_dispatcher() -> Dispatcher:
    # Диспетчер можно конфигурировать здесь (Middlewares, storage и т.д.)
    return Dispatcher()
