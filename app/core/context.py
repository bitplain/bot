"""Управление контекстом диалогов (история сообщений)."""
from __future__ import annotations

import logging
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.context import ContextMessage

logger = logging.getLogger(__name__)


class ContextManager:
    """Сохраняет и обрезает контекст до заданных лимитов."""

    def __init__(self, max_messages: int, max_chars: int):
        self.max_messages = max_messages
        self.max_chars = max_chars

    async def add_message(
        self, session: AsyncSession, user_id: int, role: str, content: str
    ) -> None:
        message = ContextMessage(user_id=user_id, role=role, content=content)
        session.add(message)
        await session.commit()
        await self.trim_history(session, user_id)

    async def get_history(self, session: AsyncSession, user_id: int) -> List[ContextMessage]:
        result = await session.execute(
            select(ContextMessage)
            .where(ContextMessage.user_id == user_id)
            .order_by(ContextMessage.id)
        )
        return list(result.scalars())

    async def trim_history(self, session: AsyncSession, user_id: int) -> None:
        history = await self.get_history(session, user_id)
        while len(history) > self.max_messages or self._length(history) > self.max_chars:
            oldest = history.pop(0)
            await session.delete(oldest)
            await session.commit()
            logger.debug("Удалено сообщение %s из контекста пользователя %s", oldest.id, user_id)

    @staticmethod
    def _length(messages: List[ContextMessage]) -> int:
        return sum(len(m.content) for m in messages)

