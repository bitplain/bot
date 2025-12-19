"""Безопасность: шифрование и ограничения доступа."""
from __future__ import annotations

import base64
import time
from collections import defaultdict
from typing import DefaultDict, Dict, Iterable, Optional

from aiogram import BaseMiddleware
from aiogram.types import Message
from cryptography.fernet import Fernet, InvalidToken


def build_fernet(secret: str) -> Optional[Fernet]:
    if not secret:
        return None
    key = secret
    if len(secret) != 44:
        key = base64.urlsafe_b64encode(secret.encode().ljust(32, b"0"))
    return Fernet(key)


def encrypt_value(fernet: Optional[Fernet], value: str) -> str:
    if fernet is None:
        return value
    return fernet.encrypt(value.encode()).decode()


def decrypt_value(fernet: Optional[Fernet], value: str) -> str:
    if fernet is None:
        return value
    try:
        return fernet.decrypt(value.encode()).decode()
    except InvalidToken:
        return ""


class AccessMiddleware(BaseMiddleware):
    """Ограничивает доступ к боту по списку allowed_users."""

    def __init__(self, allowed_users: Iterable[int]):
        self.allowed = set(allowed_users)

    async def __call__(self, handler, event, data):  # type: ignore[override]
        if not self.allowed:
            return await handler(event, data)
        if isinstance(event, Message) and event.from_user:
            if event.from_user.id not in self.allowed:
                return None
        return await handler(event, data)


class RateLimitMiddleware(BaseMiddleware):
    """Простейший rate limiting: ограничение количества сообщений в минуту."""

    def __init__(self, max_per_minute: int):
        self.max_per_minute = max_per_minute
        self._history: DefaultDict[int, list[float]] = defaultdict(list)

    async def __call__(self, handler, event, data):  # type: ignore[override]
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
            now = time.time()
            window = [t for t in self._history[user_id] if now - t < 60]
            window.append(now)
            self._history[user_id] = window
            if len(window) > self.max_per_minute:
                return None
        return await handler(event, data)


class ContextInjectorMiddleware(BaseMiddleware):
    """Передает settings/registry в конфигурацию события."""

    def __init__(self, settings, registry):
        self.settings = settings
        self.registry = registry

    async def __call__(self, handler, event, data):  # type: ignore[override]
        if hasattr(event, "conf"):
            event.conf["settings"] = self.settings
            event.conf["registry"] = self.registry
        data["settings"] = self.settings
        data["registry"] = self.registry
        return await handler(event, data)

