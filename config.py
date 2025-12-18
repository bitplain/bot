"""Конфигурация приложения.

Используется pydantic для удобного чтения переменных окружения и
централизованного хранения настроек.
"""
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter=",",
    )

    bot_token: str = Field(..., env="BOT_TOKEN")
    database_url: str = Field(
        default="sqlite+aiosqlite:///./knowledge.db", env="DATABASE_URL"
    )
    # Список включенных модулей. Позволяет легко отключать или подключать функционал.
    enabled_modules: List[str] = Field(
        default_factory=lambda: ["ai_core", "knowledge_base", "mail"]
    )
    # Алиасы команды открытия меню базы знаний (/Co-Fi недоступна как официальная команда,
    # поэтому дополнительно поддерживаем текстовый ввод /co-fi, /cofi и /co_fi).
    kb_menu_aliases: List[str] = Field(
        default_factory=lambda: ["cofi", "co_fi", "co-fi"]
    )

    # AI & маршрутизация
    openai_api_key: str | None = Field(default=None, env="OPENAI_API_KEY")
    openai_base_url: str = Field(
        default="https://api.openai.com/v1", env="OPENAI_BASE_URL"
    )
    openai_model: str = Field(default="gpt-4o-mini", env="OPENAI_MODEL")
    context_window_messages: int = Field(default=20, env="CONTEXT_WINDOW_MESSAGES")
    context_max_chars: int = Field(default=8000, env="CONTEXT_MAX_CHARS")

    # Безопасность и ограничения
    allowed_users: List[int] = Field(default_factory=list, env="ALLOWED_USERS")
    rate_limit_per_user_per_minute: int = Field(default=20, env="RATE_LIMIT_PER_MIN")
    fernet_secret: str = Field(default="", env="FERNET_SECRET")

    # Почта
    mail_host: str | None = Field(default=None, env="MAIL_HOST")
    mail_port: int = Field(default=993, env="MAIL_PORT")
    mail_use_ssl: bool = Field(default=True, env="MAIL_USE_SSL")
    mail_username: str | None = Field(default=None, env="MAIL_USERNAME")
    mail_password: str | None = Field(default=None, env="MAIL_PASSWORD")
    mail_protocol: str = Field(default="imap", env="MAIL_PROTOCOL")  # imap/pop3

    @field_validator("fernet_secret", mode="before")
    def _ensure_fernet_key(cls, value: str):  # noqa: N805 - pydantic validator
        # Пустое значение блокирует шифрование RDP, ключ генерируется отдельно.
        return value


def get_settings() -> Settings:
    """Возвращает экземпляр настроек."""

    return Settings()
