"""AI core module: маршрутизация запросов между плагинами."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from aiogram import Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import ContextManager
from app.core.db import get_session
from app.core.modules import Module, ModuleRegistry
from app.models.context import ContextMessage
from config import Settings

router = Router(name="ai_core")
logger = logging.getLogger(__name__)


class AICoreModule(Module):
    name = "ai_core"

    def __init__(self, settings: Settings, registry: ModuleRegistry):
        super().__init__(settings)
        self.registry = registry
        self.context_manager = ContextManager(
            max_messages=settings.context_window_messages,
            max_chars=settings.context_max_chars,
        )
        self.client: Optional[AsyncOpenAI] = None
        if settings.openai_api_key:
            self.client = AsyncOpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
            )

    def initialize(self, dispatcher: Dispatcher) -> None:
        dispatcher.include_router(router)

    async def process(self, user_id: int, message: str) -> str:
        # Пробуем LLM для маршрутизации; если нет ключа — простая эвристика.
        target = None
        if self.client:
            target = await self._route_with_llm(message)
        if not target:
            target = self._fallback_route(message)

        if not target:
            return "Не смог определить подходящий модуль. Уточните запрос."

        module = self.registry.get_module(target)
        if module is None:
            return "Модуль недоступен."
        return await module.process(user_id, message)

    def get_capabilities(self) -> List[str]:
        return ["route_message", "summarize_mail"]

    async def _route_with_llm(self, message: str) -> Optional[str]:
        if not self.client:
            return None
        tools = [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": ", ".join(capabilities),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "intent": {"type": "string"},
                        },
                    },
                },
            }
            for name, capabilities in self.registry.get_capabilities_map().items()
            if name != self.name
        ]
        response = await self.client.chat.completions.create(
            model=self.settings.openai_model,
            messages=[{"role": "user", "content": message}],
            tools=tools,
        )
        choice = response.choices[0]
        if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
            return choice.message.tool_calls[0].function.name
        return None

    def _fallback_route(self, message: str) -> Optional[str]:
        text = message.lower()
        if any(key in text for key in ["почт", "email", "mail"]):
            return "mail"
        if any(key in text for key in ["rdp", "удален", "доступ"]):
            return "knowledge_base"
        return "knowledge_base"


@router.message(Command("ai"))
async def ask_ai(message: Message, state):
    """Маршрутизация пользовательского текста через AI ядро."""

    text = (message.text or "").partition(" ")[2].strip()
    if not text:
        await message.answer("Отправьте вопрос после команды /ai")
        return

    registry: ModuleRegistry = message.conf.get("registry")  # type: ignore[attr-defined]
    ai_core: AICoreModule = registry.get_module("ai_core")  # type: ignore[assignment]

    async for session in get_session():
        assert isinstance(session, AsyncSession)
        await ai_core.context_manager.add_message(session, message.from_user.id, "user", text)
        reply = await ai_core.process(message.from_user.id, text)
        await ai_core.context_manager.add_message(session, message.from_user.id, "assistant", reply)
        await message.answer(reply)
        break

