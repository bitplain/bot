# Модульный Telegram-бот с AI-ядром

Пример асинхронного бота на `aiogram 3` с архитектурой «плагины + AI-роутер».
Центральный AI-модуль хранит контекст диалога, применяет function-calling (OpenAI
совместимый API) и эвристику, выбирая подходящий модуль. Реализованы три модуля:

- `ai_core` — центральное ядро: управляет контекстом, маршрутизирует запросы между
  модулями через function calling (OpenAI API) и эвристику.
- `knowledge_base` — база знаний сотрудников: добавление, поиск, удаление, список,
  сохранение RDP-учёток с шифрованием (Fernet).
- `mail` — получение писем по IMAP/POP3, парсинг вложений и AI-анализ.

Архитектура использует паттерн «Plugin System»: каждый модуль наследуется от базового
`Module`, реализует `initialize`, `process`, `get_capabilities`, регистрируется через
`ModuleRegistry` и может быть включён/выключен в конфигурации. AI-ядро изолирует
сбои модулей и возвращает контролируемые ошибки.

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
│       │   └── module.py       # AI-ядро: контекст, function calling, маршрутизация /ai
│       ├── knowledge_base
│       │   ├── handlers.py     # /Co-Fi меню, CRUD, сбор RDP с шифрованием
│       │   └── module.py
│       └── mail
│           └── module.py       # Получение писем, вложения и AI-анализ
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

Шифрование RDP происходит через `cryptography.Fernet`; ключ задаётся `FERNET_SECRET`
(не менее 32 символов). Без ключа RDP-данные не сохраняются.

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
   - `FERNET_SECRET` — 32+ символа для шифрования RDP (обязателен, если хотите хранить RDP).
   - `ALLOWED_USERS` — список Telegram ID через запятую (пусто = без ограничений).
   - `ENABLED_MODULES` — список активных модулей (по умолчанию ai_core,knowledge_base,mail).
   - `KB_MENU_ALIASES` — алиасы для вызова меню базы знаний (/cofi,/co_fi,/co-fi).
   - `MAIL_*` — настройки IMAP/POP3, если нужен модуль почты.
3. Запустите бота:
   ```bash
   python main.py
   ```
   При старте создаются таблицы, включаются модули из `enabled_modules` в `config.py` или `.env`,
   подключаются middlewares для ACL, rate limit и контекста.

## Использование
- `/ai <запрос>` — отправить текст в AI-ядро, которое выберет модуль (БЗ, почта и т.п.).
- `/cofi` или текст `/Co-Fi` — меню базы знаний с кнопками «Добавить», «Поиск»,
  «Удалить», «Список» (5 записей на страницу).
- `/add` — диалог добавления сотрудника + опциональный сбор RDP (хост, логин, пароль,
  порт). Данные валидируются, RDP сохраняется зашифрованным и привязывается к Telegram
  пользователю.
- `/mail` — получить крайнее письмо (IMAP/POP3) и выдать краткий AI-анализ.

## Контекстное окно и лимиты
`ContextManager` сохраняет историю в таблицу `context_history`, подгружает её при
обращении и обрезает при превышении `CONTEXT_WINDOW_MESSAGES` или `CONTEXT_MAX_CHARS`.
AI-ядро использует историю при маршрутизации. При невозможности определить модуль
возвращает список доступных модулей вместо ошибки.

## Расширение
1. Создайте пакет `app/modules/<new_module>` с классом, наследующим `Module`.
2. Реализуйте методы `initialize`, `process`, `get_capabilities` и зарегистрируйте
   роутеры/handlers внутри `initialize`.
3. Добавьте имя модуля в `enabled_modules` (в `config.py` или через переменные окружения).
4. AI-ядро автоматически увидит новый модуль и сможет вызвать его через function
   calling/эвристику.

## Безопасность и эксплуатация
- Access control: `ALLOWED_USERS` ограничивает доступ. Rate limit: `RATE_LIMIT_PER_MIN` с сообщением пользователю.
- RDP-логин/пароль шифруются через Fernet. Без `FERNET_SECRET` сохранение RDP блокируется.
- Валидация email/телефона предотвращает некорректный ввод.
- Graceful shutdown: при остановке закрывается polling, HTTP-сессия бота и соединения с БД.
- Ограничения Telegram по размеру сообщения учитываются при дроблении длинных ответов и пагинации списка сотрудников.

## Пример добавления нового модуля
Комментарий в `app/core/modules.py` демонстрирует шаблон. Достаточно реализовать
класс, добавить в конфиг — остальной код менять не нужно.
