"""Регистрация модулей по списку из конфигурации."""
from aiogram import Dispatcher


def register_enabled_modules(dispatcher: Dispatcher, enabled: list[str]):
    """Подключает обработчики всех активных модулей.

    Чтобы добавить новый модуль, создайте пакет ``app.modules.<module_name>`` и
    реализуйте функцию ``setup(router_or_dispatcher)`` внутри него. Затем
    добавьте имя модуля в ``enabled_modules`` конфигурации.
    """

    for module_name in enabled:
        match module_name:
            case "knowledge_base":
                from app.modules.knowledge_base.handlers import setup as kb_setup

                kb_setup(dispatcher)
            # Шаблон для будущих модулей:
            # case "search":
            #     from app.modules.search.handlers import setup as search_setup
            #     search_setup(dispatcher)
            case _:
                raise ValueError(f"Неизвестный модуль: {module_name}")
