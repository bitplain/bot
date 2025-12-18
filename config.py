"""Конфигурация приложения.

Используется pydantic для удобного чтения переменных окружения и
централизованного хранения настроек.
"""
from pydantic import BaseSettings, Field
from typing import List


class Settings(BaseSettings):
    bot_token: str = Field(..., env="BOT_TOKEN")
    database_url: str = Field(
        default="sqlite+aiosqlite:///./knowledge.db", env="DATABASE_URL"
    )
    # Список включенных модулей. Позволяет легко отключать или подключать функционал.
    enabled_modules: List[str] = Field(default_factory=lambda: ["knowledge_base"])

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def get_settings() -> Settings:
    """Возвращает синглтон настроек.

    Оборачиваем в функцию, чтобы не создавать глобальных состояний во время
    импортов (упрощает тестирование и статический анализ).
    """

    return Settings()
