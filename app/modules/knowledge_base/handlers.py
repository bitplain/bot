"""Обработчики модуля базы знаний сотрудников."""
import logging
import re
from dataclasses import dataclass
from typing import Iterable, TYPE_CHECKING

from aiogram import Dispatcher, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.models import Employee
from config import Settings

if TYPE_CHECKING:  # pragma: no cover - только для типов
    from app.modules.knowledge_base.module import KnowledgeBaseModule

router = Router(name="knowledge_base")
logger = logging.getLogger(__name__)


class AddEmployeeStates(StatesGroup):
    last_name = State()
    first_name = State()
    middle_name = State()
    phone = State()
    email = State()
    position = State()
    department = State()
    rdp_host = State()
    rdp_login = State()
    rdp_password = State()
    rdp_port = State()


class SearchStates(StatesGroup):
    query = State()


class DeleteStates(StatesGroup):
    target = State()


@dataclass
class EmployeePayload:
    last_name: str
    first_name: str
    middle_name: str | None
    phone: str
    email: str
    position: str
    department: str
    rdp_host: str | None = None
    rdp_login: str | None = None
    rdp_password: str | None = None
    rdp_port: int | None = None


_PHONE_RE = re.compile(r"^\+?[\d\s\-()]{7,20}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_MENU_TRIGGERS: set[str] = set()
_MODULE: "KnowledgeBaseModule | None" = None


def _normalize_triggers(raw: Iterable[str] | None) -> set[str]:
    if not raw:
        return set()
    normalized = set()
    for item in raw:
        alias = item.strip()
        if not alias:
            continue
        alias = alias.lower()
        if alias.startswith("/"):
            normalized.add(alias)
        else:
            normalized.add(f"/{alias}")
    return normalized


def _menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить", callback_data="kb:add")
    builder.button(text="🔍 Поиск", callback_data="kb:search")
    builder.button(text="🗑 Удалить", callback_data="kb:delete")
    builder.button(text="📋 Список", callback_data="kb:list:0")
    builder.adjust(2, 2)
    return builder.as_markup()


@router.message(Command("cofi"))
@router.message(Command("co_fi"))
async def open_menu(message: Message, state: FSMContext):
    """Показывает главное меню работы с базой знаний."""

    await state.clear()
    await message.answer(
        "Добро пожаловать в модуль базы знаний сотрудников. Выберите действие:",
        reply_markup=_menu_keyboard(),
    )


@router.message(lambda m: (m.text or "").split()[0].lower() in _MENU_TRIGGERS)
async def open_menu_text(message: Message, state: FSMContext):
    """Обработчик текстовых команд вида /Co-Fi или /co-fi."""

    await open_menu(message, state)


@router.callback_query(lambda c: c.data == "kb:add")
async def open_add_from_menu(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    if callback.message:
        await start_add(callback.message, state)


@router.callback_query(lambda c: c.data == "kb:menu")
async def return_to_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат к главному меню модуля."""

    await callback.answer()
    await state.clear()
    if callback.message:
        try:
            await callback.message.edit_text(
                "Выберите действие:", reply_markup=_menu_keyboard()
            )
        except TelegramBadRequest:
            await callback.message.answer(
                "Выберите действие:", reply_markup=_menu_keyboard()
            )


@router.message(Command("add"))
@router.message(Command("добавить"))
async def start_add(message: Message, state: FSMContext):
    """Стартуем диалог добавления пользователя."""

    await state.set_state(AddEmployeeStates.last_name)
    await message.answer("Введите фамилию сотрудника:")


@router.message(AddEmployeeStates.last_name)
async def input_last_name(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Фамилия не может быть пустой. Повторите ввод:")
        return
    await state.update_data(last_name=message.text.strip())
    await state.set_state(AddEmployeeStates.first_name)
    await message.answer("Введите имя сотрудника:")


@router.message(AddEmployeeStates.first_name)
async def input_first_name(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Имя не может быть пустым. Повторите ввод:")
        return
    await state.update_data(first_name=message.text.strip())
    await state.set_state(AddEmployeeStates.middle_name)
    await message.answer(
        "Введите отчество сотрудника (или '-' если отсутствует):"
    )


@router.message(AddEmployeeStates.middle_name)
async def input_middle_name(message: Message, state: FSMContext):
    middle = message.text.strip() if message.text else ""
    await state.update_data(middle_name=None if middle in {"-", ""} else middle)
    await state.set_state(AddEmployeeStates.phone)
    await message.answer("Введите номер телефона (+79998887766):")


@router.message(AddEmployeeStates.phone)
async def input_phone(message: Message, state: FSMContext):
    phone = message.text.strip() if message.text else ""
    if not _PHONE_RE.match(phone):
        await message.answer(
            "Телефон должен содержать только цифры, пробелы, '+', '-', '()' и быть длиной от 7 до 20 символов. Попробуйте снова:"
        )
        return
    await state.update_data(phone=phone)
    await state.set_state(AddEmployeeStates.email)
    await message.answer("Введите email сотрудника:")


@router.message(AddEmployeeStates.email)
async def input_email(message: Message, state: FSMContext):
    email = message.text.strip() if message.text else ""
    if not _EMAIL_RE.match(email):
        await message.answer("Некорректный email. Введите адрес в формате user@example.com")
        return
    await state.update_data(email=email)
    await state.set_state(AddEmployeeStates.position)
    await message.answer("Введите должность сотрудника:")


@router.message(AddEmployeeStates.position)
async def input_position(message: Message, state: FSMContext):
    position = message.text.strip() if message.text else ""
    if not position:
        await message.answer("Должность не может быть пустой. Повторите ввод:")
        return
    await state.update_data(position=position)
    await state.set_state(AddEmployeeStates.department)
    await message.answer("Введите отдел сотрудника:")


@router.message(AddEmployeeStates.department)
async def input_department(message: Message, state: FSMContext):
    department = message.text.strip() if message.text else ""
    if not department:
        await message.answer("Отдел не может быть пустым. Повторите ввод:")
        return

    await state.update_data(department=department)
    await state.set_state(AddEmployeeStates.rdp_host)
    await message.answer(
        "Укажите RDP-хост (или '-' чтобы пропустить сохранение учётных данных):"
    )


@router.message(AddEmployeeStates.rdp_host)
async def input_rdp_host(message: Message, state: FSMContext):
    host = (message.text or "").strip()
    if host == "-" or not host:
        await state.update_data(rdp_host=None)
        await _finalize_employee(message, state)
        return
    await state.update_data(rdp_host=host)
    await state.set_state(AddEmployeeStates.rdp_login)
    await message.answer("Введите RDP логин:")


@router.message(AddEmployeeStates.rdp_login)
async def input_rdp_login(message: Message, state: FSMContext):
    login = (message.text or "").strip()
    if not login:
        await message.answer("Логин не может быть пустым. Повторите ввод или отправьте '-' для пропуска")
        return
    await state.update_data(rdp_login=login)
    await state.set_state(AddEmployeeStates.rdp_password)
    await message.answer("Введите RDP пароль:")


@router.message(AddEmployeeStates.rdp_password)
async def input_rdp_password(message: Message, state: FSMContext):
    password = (message.text or "").strip()
    if not password:
        await message.answer("Пароль не может быть пустым. Повторите ввод:")
        return
    await state.update_data(rdp_password=password)
    await state.set_state(AddEmployeeStates.rdp_port)
    await message.answer("Введите порт RDP (по умолчанию 3389):")


@router.message(AddEmployeeStates.rdp_port)
async def input_rdp_port(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    port = 3389
    if text:
        if not text.isdigit():
            await message.answer("Порт должен быть числом. Попробуйте снова:")
            return
        port = int(text)
    await state.update_data(rdp_port=port)
    await _finalize_employee(message, state)


async def _finalize_employee(message: Message, state: FSMContext):
    data = await state.get_data()
    payload = EmployeePayload(**data)  # type: ignore[arg-type]

    try:
        await _save_employee(payload, message.from_user)
    except Exception as exc:  # pragma: no cover - простая логика
        await message.answer(
            "Не удалось сохранить данные. Попробуйте позднее или обратитесь к администратору."
        )
        logger.exception("Ошибка при сохранении сотрудника", exc_info=exc)
        await state.clear()
        return

    reply_parts = [
        "Сотрудник успешно добавлен:\n",
        f"<b>{payload.last_name} {payload.first_name}</b>\n",
        f"Email: {payload.email}\nТелефон: {payload.phone}\n",
        f"Должность: {payload.position}\nОтдел: {payload.department}\n",
    ]
    if payload.rdp_host:
        reply_parts.append("Учётные данные RDP сохранены и зашифрованы.")
    await message.answer("".join(reply_parts))
    await state.clear()


@router.callback_query(lambda c: c.data == "kb:search")
async def start_search(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(SearchStates.query)
    if callback.message:
        await callback.message.answer(
            "Введите запрос для поиска (фамилия, телефон, email или отдел):"
        )


@router.message(SearchStates.query)
async def process_search(message: Message, state: FSMContext):
    query = (message.text or "").strip()
    if not query:
        await message.answer("Запрос не может быть пустым. Введите текст для поиска:")
        return

    async for session in get_session():
        assert isinstance(session, AsyncSession)
        stmt = select(Employee).where(
            or_(
                Employee.last_name.ilike(f"%{query}%"),
                Employee.first_name.ilike(f"%{query}%"),
                Employee.middle_name.ilike(f"%{query}%"),
                Employee.phone.ilike(f"%{query}%"),
                Employee.email.ilike(f"%{query}%"),
                Employee.position.ilike(f"%{query}%"),
                Employee.department.ilike(f"%{query}%"),
            )
        ).limit(10)
        result = await session.execute(stmt)
        employees = result.scalars().all()

    if not employees:
        await message.answer("Ничего не найдено. Попробуйте другой запрос.")
        await state.clear()
        return

    lines = [
        "Найдены сотрудники:",
        *[
            f"#{emp.id}: {emp.last_name} {emp.first_name} ({emp.position})\n"
            f"Тел.: {emp.phone}, Email: {emp.email}"
            for emp in employees
        ],
    ]
    await message.answer("\n\n".join(lines))
    await state.clear()


@router.callback_query(lambda c: c.data == "kb:delete")
async def start_delete(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(DeleteStates.target)
    if callback.message:
        await callback.message.answer(
            "Введите ID или email сотрудника, которого нужно удалить:"
        )


@router.message(DeleteStates.target)
async def process_delete(message: Message, state: FSMContext):
    target = (message.text or "").strip()
    if not target:
        await message.answer("Пожалуйста, введите ID или email сотрудника:")
        return

    async for session in get_session():
        assert isinstance(session, AsyncSession)
        stmt = select(Employee)
        employee = None
        if target.isdigit():
            employee = await session.get(Employee, int(target))
        else:
            stmt = stmt.where(Employee.email == target)
            result = await session.execute(stmt)
            employee = result.scalars().first()

        if not employee:
            await message.answer("Сотрудник не найден. Проверьте ввод и попробуйте снова.")
            await state.clear()
            return

        async with session.begin():
            await session.delete(employee)

    await message.answer("Сотрудник удалён из базы знаний.")
    await state.clear()


@router.callback_query(lambda c: c.data and c.data.startswith("kb:list:"))
async def list_employees(callback: CallbackQuery):
    """Отображает сотрудников постранично по 5 записей."""

    await callback.answer()
    try:
        page = int(callback.data.split(":")[-1])
    except (ValueError, AttributeError):
        page = 0

    page_size = 5
    offset = page * page_size

    async for session in get_session():
        assert isinstance(session, AsyncSession)
        total_stmt = select(func.count()).select_from(Employee)
        total_result = await session.execute(total_stmt)
        total = total_result.scalar_one()

        stmt = (
            select(Employee)
            .order_by(Employee.id)
            .offset(offset)
            .limit(page_size)
        )
        rows = await session.execute(stmt)
        employees = rows.scalars().all()

    if not employees:
        text = "В базе пока нет сотрудников." if total == 0 else "Страница пуста."
        if callback.message:
            await callback.message.answer(text, reply_markup=_menu_keyboard())
        return

    lines = [
        "Список сотрудников (по 5 на страницу):",
        *[
            f"#{emp.id}: {emp.last_name} {emp.first_name}\n"
            f"Email: {emp.email}, Тел.: {emp.phone}\n"
            f"Должность: {emp.position}, Отдел: {emp.department}"
            for emp in employees
        ],
        f"Страница {page + 1} из {(total + page_size - 1) // page_size}",
    ]

    builder = InlineKeyboardBuilder()
    if offset > 0:
        builder.button(text="⬅️ Назад", callback_data=f"kb:list:{page - 1}")
    if offset + page_size < total:
        builder.button(text="➡️ Далее", callback_data=f"kb:list:{page + 1}")
    builder.button(text="🏠 Меню", callback_data="kb:menu")
    builder.adjust(2, 1)

    try:
        if callback.message:
            await callback.message.edit_text("\n\n".join(lines), reply_markup=builder.as_markup())
    except TelegramBadRequest:
        # Сообщение могло быть удалено или содержать неизменяемый текст
        if callback.message:
            await callback.message.answer("\n\n".join(lines), reply_markup=builder.as_markup())


async def _save_employee(payload: EmployeePayload, telegram_user) -> None:
    """Сохраняет запись в базу данных."""

    async for session in get_session():
        assert isinstance(session, AsyncSession)
        employee = Employee(
            last_name=payload.last_name,
            first_name=payload.first_name,
            middle_name=payload.middle_name,
            phone=payload.phone,
            email=payload.email,
            position=payload.position,
            department=payload.department,
        )
        async with session.begin():
            session.add(employee)
        if payload.rdp_host and _MODULE:
            await _MODULE.store_rdp(
                session,
                telegram_id=telegram_user.id,
                username=getattr(telegram_user, "username", None),
                login=payload.rdp_login or "",
                password=payload.rdp_password or "",
                host=payload.rdp_host,
                port=payload.rdp_port or 3389,
            )


def setup(
    dispatcher: Dispatcher,
    settings: Settings | None = None,
    module: "KnowledgeBaseModule | None" = None,
):
    """Подключение роутера модуля."""

    global _MENU_TRIGGERS
    _MENU_TRIGGERS = _normalize_triggers(
        settings.kb_menu_aliases if settings else ["cofi", "co_fi", "co-fi"]
    )
    global _MODULE
    _MODULE = module

    dispatcher.include_router(router)
