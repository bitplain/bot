"""Обработчики модуля базы знаний сотрудников."""
import logging
import re
from dataclasses import dataclass

from aiogram import Dispatcher, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.models import Employee

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


@dataclass
class EmployeePayload:
    last_name: str
    first_name: str
    middle_name: str | None
    phone: str
    email: str
    position: str
    department: str


_PHONE_RE = re.compile(r"^\+?[\d\s\-()]{7,20}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


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
    data = await state.get_data()
    payload = EmployeePayload(**data)  # type: ignore[arg-type]

    try:
        await _save_employee(payload)
    except Exception as exc:  # pragma: no cover - простая логика
        await message.answer(
            "Не удалось сохранить данные. Попробуйте позднее или обратитесь к администратору."
        )
        logger.exception("Ошибка при сохранении сотрудника", exc_info=exc)
        await state.clear()
        return

    await message.answer(
        "Сотрудник успешно добавлен:\n"
        f"<b>{payload.last_name} {payload.first_name}</b>\n"
        f"Email: {payload.email}\nТелефон: {payload.phone}\n"
        f"Должность: {payload.position}\nОтдел: {payload.department}"
    )
    await state.clear()


async def _save_employee(payload: EmployeePayload) -> None:
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


def setup(dispatcher: Dispatcher):
    """Подключение роутера модуля."""

    dispatcher.include_router(router)
