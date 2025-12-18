"""Инициализация базы данных и сессий SQLAlchemy."""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Базовый класс моделей."""


_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_engine(database_url: str):
    """Создает движок и фабрику сессий.

    Вызывается один раз при старте приложения. Для миграции на PostgreSQL/MySQL
    достаточно поменять ``database_url``.
    """

    global _engine, _session_factory
    _engine = create_async_engine(database_url, echo=False, future=True)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Зависимость для получения сессии."""

    if _session_factory is None:
        raise RuntimeError("База данных не инициализирована. Вызовите init_engine().")
    async with _session_factory() as session:
        yield session


async def create_db():
    """Создает таблицы (миграции можно добавить позднее)."""

    if _engine is None:
        raise RuntimeError("База данных не инициализирована. Вызовите init_engine().")

    from app.models import Base as ModelBase  # локальный импорт чтобы избежать циклов

    async with _engine.begin() as conn:
        await conn.run_sync(ModelBase.metadata.create_all)
