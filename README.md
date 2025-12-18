# Модульный Telegram-бот с AI-ядром

Пример асинхронного бота на `aiogram 3`, где AI-ядро маршрутизирует запросы к
подключаемым модулям. Реализованы три модуля:

- `ai_core` — центральное ядро: управляет контекстом, маршрутизирует запросы между
  модулями через function calling (OpenAI API) и эвристику.
- `knowledge_base` — база знаний сотрудников: добавление, поиск, удаление, список,
  сохранение RDP-учёток с шифрованием.
- `mail` — получение писем по IMAP/POP3 и их AI-анализ.

Архитектура использует паттерн «Plugin System»: каждый модуль наследуется от базового
`Module`, реализует `initialize`, `process`, `get_capabilities`, регистрируется через
`ModuleRegistry` и может быть включён/выключен в конфигурации.

## Структура
```
.
├── app
│   ├── core
│   │   ├── context.py          # Контекстное окно (история диалогов)
│   │   ├── db.py               # Async SQLAlchemy и создание схемы
│   │   ├── loader.py           # Bot/Dispatcher фабрики
│   │   ├── modules.py          # Базовый класс Module и ModuleRegistry
│   │   └── security.py         # Шифрование, ACL, rate limit, DI middleware
│   ├── models
│   │   ├── __init__.py
│   │   ├── context.py          # context_history
│   │   ├── knowledge_base.py   # employees
│   │   └── user.py             # users, rdp_credentials
│   └── modules
│       ├── ai_core
│       │   └── module.py       # AI-ядро и маршрутизация /ai
│       ├── knowledge_base
│       │   ├── handlers.py     # /Co-Fi меню, CRUD, RDP сбор
│       │   └── module.py
│       └── mail
│           └── module.py       # Получение писем и AI-анализ
├── config.py                   # Pydantic-настройки
├── .env.example                # Пример окружения
├── main.py                     # Точка входа и graceful shutdown
├── requirements.txt
└── README.md
```

## База данных
SQLite (по умолчанию) или PostgreSQL/MySQL через `DATABASE_URL`.

Таблицы:
- `users` — `telegram_id`, `username`, `created_at`.
- `rdp_credentials` — `encrypted_login`, `encrypted_password`, `host`, `port`, FK на `users`.
- `employees` — ФИО, телефон, email, должность, отдел.
- `context_history` — роль (`user/assistant`), текст, timestamp (можно заменить на
  авто-дату при миграции).

Шифрование RDP происходит через `cryptography.Fernet`; ключ задаётся `FERNET_SECRET`.

## Настройка
1. Склонируйте репозиторий и установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```
2. Создайте `.env` на основе `.env.example` и заполните:
   - `BOT_TOKEN` — токен бота.
   - `OPENAI_API_KEY` — для маршрутизации и AI-анализа (опционально; без него работает
     эвристика и часть функционала).
   - `DATABASE_URL` — при необходимости замените на PostgreSQL/MySQL.
   - `FERNET_SECRET` — 32+ символа для шифрования RDP.
   - `ALLOWED_USERS` — список Telegram ID через запятую (пусто = без ограничений).
   - `MAIL_*` — настройки IMAP/POP3, если нужен модуль почты.
3. Запустите бота:
   ```bash
   python main.py
   ```
   При старте создаются таблицы, включаются модули из `enabled_modules` в `config.py`.

## Использование
- `/ai <запрос>` — отправить текст в AI-ядро, которое выберет модуль (БЗ, почта и т.п.).
- `/cofi` или текст `/Co-Fi` — меню базы знаний с кнопками «Добавить», «Поиск»,
  «Удалить», «Список» (5 записей на страницу).
- `/add` — диалог добавления сотрудника + опциональный сбор RDP (хост, логин, пароль,
  порт). Данные валидируются, RDP сохраняется зашифрованным и привязывается к Telegram
  пользователю.
- `/mail` — получить крайнее письмо (IMAP/POP3) и выдать краткий AI-анализ.

## Контекстное окно и лимиты
Класс `ContextManager` хранит последние `CONTEXT_WINDOW_MESSAGES` сообщений или пока
суммарная длина не превышает `CONTEXT_MAX_CHARS`. При превышении старые записи
удаляются. Контекст используется AI-ядром и сохраняется в БД.

## Расширение
1. Создайте пакет `app/modules/<new_module>` с классом, наследующим `Module`.
2. Реализуйте методы `initialize`, `process`, `get_capabilities` и зарегистрируйте
   роутеры/handlers внутри `initialize`.
3. Добавьте имя модуля в `enabled_modules` (в `config.py` или через переменные окружения).
4. AI-ядро автоматически увидит новый модуль и сможет вызвать его через function
   calling/эвристику.

## Безопасность и эксплуатация
- Access control: `ALLOWED_USERS` ограничивает доступ. Rate limit: `RATE_LIMIT_PER_MIN`.
- RDP-логин/пароль шифруются через Fernet. При отсутствии ключа сохраняются в открытом
  виде — ключ обязателен для продакшена.
- Валидация email/телефона предотвращает некорректный ввод.
- Graceful shutdown: при остановке корректно завершается polling.
- Ограничения Telegram по размеру сообщения учитывайте при формировании ответов
  (пагинация списка сотрудников).

## Пример добавления нового модуля
Комментарий в `app/core/modules.py` демонстрирует шаблон. Достаточно реализовать
класс, добавить в конфиг — остальной код менять не нужно.
