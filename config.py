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
    enabled_modules: List[str] = Field(
        default_factory=lambda: ["knowledge_base", "ai_assistant"]
    )
    openai_api_key: str | None = Field(default=None, env="OPENAI_API_KEY")
    openai_base_url: str = Field(
        default="https://api.openai.com/v1", env="OPENAI_BASE_URL"
    )
    openai_model: str = Field(default="gpt-3.5-turbo", env="OPENAI_MODEL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def get_settings() -> Settings:
    """Возвращает синглтон настроек.

    Оборачиваем в функцию, чтобы не создавать глобальных состояний во время
    импортов (упрощает тестирование и статический анализ).
    """

    return Settings()
