"""Простой модуль общения с ИИ через совместимый с ChatGPT API."""
from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx
from aiogram import Dispatcher, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from config import get_settings

router = Router(name="ai_assistant")
logger = logging.getLogger(__name__)


class AskAIStates(StatesGroup):
    waiting_question = State()


@dataclass(slots=True)
class AIConfig:
    api_key: str
    base_url: str
    model: str


async def _load_ai_config() -> AIConfig | None:
    settings = get_settings()
    if not settings.openai_api_key:
        return None
    return AIConfig(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url.rstrip("/"),
        model=settings.openai_model,
    )


@router.message(Command("ai"))
@router.message(Command("ask"))
async def start_ai(message: Message, state: FSMContext):
    """Начинает диалог с ИИ или сразу отвечает, если вопрос передан в команде."""

    config = await _load_ai_config()
    if config is None:
        await message.answer(
            "Модуль ИИ не настроен. Укажите переменную окружения OPENAI_API_KEY."
        )
        return

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await state.set_state(AskAIStates.waiting_question)
        await message.answer("Задайте вопрос для ИИ в следующем сообщении.")
        return

    await _send_ai_reply(message, parts[1], config)
    await state.clear()


@router.message(AskAIStates.waiting_question)
async def handle_question(message: Message, state: FSMContext):
    """Отвечает на вопрос после команды /ai без аргумента."""

    config = await _load_ai_config()
    if config is None:
        await message.answer(
            "Модуль ИИ не настроен. Укажите переменную окружения OPENAI_API_KEY."
        )
        await state.clear()
        return

    question = (message.text or "").strip()
    if not question:
        await message.answer("Вопрос не может быть пустым. Попробуйте снова.")
        return

    await _send_ai_reply(message, question, config)
    await state.clear()


async def _send_ai_reply(message: Message, question: str, config: AIConfig):
    """Вызывает чат-модель и отправляет ответ пользователю."""

    await message.answer("Думаю над ответом...")

    payload = {
        "model": config.model,
        "messages": [
            {
                "role": "system",
                "content": "Ты корпоративный ассистент и отвечаешь кратко и по делу.",
            },
            {"role": "user", "content": question},
        ],
        "temperature": 0.2,
    }

    headers = {"Authorization": f"Bearer {config.api_key}"}
    url = f"{config.base_url}/chat/completions"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            answer = data["choices"][0]["message"]["content"].strip()
    except Exception as exc:  # pragma: no cover - внешние ошибки
        logger.exception("Не удалось получить ответ от ИИ", exc_info=exc)
        await message.answer(
            "Не получилось обратиться к модели. Проверьте ключ API/доступ и попробуйте ещё раз."
        )
        return

    await message.answer(answer)


def setup(dispatcher: Dispatcher):
    dispatcher.include_router(router)
