"""Класс модуля базы знаний."""
from __future__ import annotations

from aiogram import Dispatcher
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.modules import Module
from app.core.security import decrypt_value, encrypt_value, build_fernet
from app.models import Employee, RDPCredential, User
from config import Settings

from . import handlers


class KnowledgeBaseModule(Module):
    name = "knowledge_base"

    def __init__(self, settings: Settings):
        super().__init__(settings)
        self.fernet = build_fernet(settings.fernet_secret)

    def initialize(self, dispatcher: Dispatcher) -> None:
        handlers.setup(dispatcher, settings=self.settings, module=self)

    async def process(self, user_id: int, message: str) -> str:
        # Простейший поиск по таблице сотрудников
        async for session in get_session():
            assert isinstance(session, AsyncSession)
            stmt = select(Employee).where(Employee.last_name.ilike(f"%{message}%"))
            result = await session.execute(stmt)
            employees = list(result.scalars())
            if not employees:
                return "Ничего не найдено в базе знаний."
            formatted = "\n\n".join(
                f"{emp.last_name} {emp.first_name} — {emp.position} ({emp.department}), "
                f"тел. {emp.phone}, email {emp.email}"
                for emp in employees[:5]
            )
            return formatted
        return "Нет доступа к базе данных."

    def get_capabilities(self):
        return ["search_employee", "store_rdp", "list_employees"]

    async def store_rdp(
        self, session: AsyncSession, telegram_id: int, username: str | None, login: str, password: str, host: str, port: int
    ) -> None:
        if self.fernet is None:
            raise RuntimeError("FERNET_SECRET не задан, шифрование RDP недоступно.")
        user = await self._get_or_create_user(session, telegram_id, username)
        credential = RDPCredential(
            user_id=user.id,
            encrypted_login=encrypt_value(self.fernet, login),
            encrypted_password=encrypt_value(self.fernet, password),
            host=host,
            port=port,
        )
        session.add(credential)
        await session.commit()

    async def fetch_rdp(self, session: AsyncSession, telegram_id: int):
        stmt = (
            select(RDPCredential, User)
            .join(User, RDPCredential.user_id == User.id)
            .where(User.telegram_id == telegram_id)
        )
        result = await session.execute(stmt)
        creds = []
        for cred, user in result.all():
            creds.append(
                {
                    "login": decrypt_value(self.fernet, cred.encrypted_login),
                    "password": decrypt_value(self.fernet, cred.encrypted_password),
                    "host": cred.host,
                    "port": cred.port,
                }
            )
        return creds

    @staticmethod
    async def _get_or_create_user(
        session: AsyncSession, telegram_id: int, username: str | None
    ) -> User:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user:
            return user
        user = User(telegram_id=telegram_id, username=username)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user
