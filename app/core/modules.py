"""Плагин-система модулей и их регистрация."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from aiogram import Dispatcher

from config import Settings

logger = logging.getLogger(__name__)


class Module(ABC):
    """Базовый класс для модулей.

    Каждый модуль должен объявлять свои возможности (`get_capabilities`) и реализовать
    бизнес-логику в `process` (используется AI-маршрутизацией) и `initialize` для
    регистрации хэндлеров/подписок.
    """

    name: str

    def __init__(self, settings: Settings):
        self.settings = settings

    @abstractmethod
    def initialize(self, dispatcher: Dispatcher) -> None:
        """Подключает маршруты/хэндлеры модуля."""

    @abstractmethod
    async def process(self, user_id: int, message: str) -> str:
        """Асинхронная обработка запроса, вызываемая AI-роутером."""

    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Список поддерживаемых задач (для AI function-calling)."""


class ModuleRegistry:
    """Регистрирует и хранит модули."""

    def __init__(self, dispatcher: Dispatcher, settings: Settings):
        self.dispatcher = dispatcher
        self.settings = settings
        self.modules: Dict[str, Module] = {}

    def load_modules(self) -> None:
        """Инициализирует модули согласно конфигурации."""

        for module_name in self.settings.enabled_modules:
            module = self._create_module(module_name)
            module.initialize(self.dispatcher)
            self.modules[module_name] = module
            logger.info("Модуль '%s' инициализирован", module_name)

    def _create_module(self, module_name: str) -> Module:
        match module_name:
            case "ai_core":
                from app.modules.ai_core.module import AICoreModule

                return AICoreModule(self.settings, self)
            case "knowledge_base":
                from app.modules.knowledge_base.module import KnowledgeBaseModule

                return KnowledgeBaseModule(self.settings)
            case "mail":
                from app.modules.mail.module import MailModule

                return MailModule(self.settings)
            case _:
                raise ValueError(f"Неизвестный модуль: {module_name}")

    def get_module(self, name: str) -> Optional[Module]:
        return self.modules.get(name)

    def get_capabilities_map(self) -> Dict[str, List[str]]:
        return {name: module.get_capabilities() for name, module in self.modules.items()}

