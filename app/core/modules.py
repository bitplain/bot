"""Регистрация модулей по списку из конфигурации."""
from aiogram import Dispatcher

from config import Settings


def register_enabled_modules(dispatcher: Dispatcher, settings: Settings):
    """Подключает обработчики всех активных модулей.

    Чтобы добавить новый модуль, создайте пакет ``app.modules.<module_name>`` и
    реализуйте функцию ``setup(router_or_dispatcher)`` внутри него. Затем
    добавьте имя модуля в ``enabled_modules`` конфигурации.
    """

    for module_name in settings.enabled_modules:
        match module_name:
            case "knowledge_base":
                from app.modules.knowledge_base.handlers import setup as kb_setup

                kb_setup(dispatcher, settings=settings)
            case "ai_assistant":
                from app.modules.ai_assistant.handlers import setup as ai_setup

                ai_setup(dispatcher, settings=settings)
            # Шаблон для будущих модулей:
            # case "search":
            #     from app.modules.search.handlers import setup as search_setup
            #     search_setup(dispatcher, settings=settings)
            case _:
                raise ValueError(f"Неизвестный модуль: {module_name}")
