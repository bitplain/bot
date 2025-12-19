"""Конфигурация приложения.

Используется pydantic для удобного чтения переменных окружения и
централизованного хранения настроек.
"""

    bot_token: str = Field(..., env="BOT_TOKEN")
    database_url: str = Field(
        default="sqlite+aiosqlite:///./knowledge.db", env="DATABASE_URL"
    )
    # Список включенных модулей. Позволяет легко отключать или подключать функционал.


    return Settings()
