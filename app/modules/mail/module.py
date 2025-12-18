"""Модуль обработки почты с ИИ-анализом."""
from __future__ import annotations

import email
import imaplib
import poplib
from email.message import Message as EmailMessage
from typing import List, Optional

from aiogram import Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message
from openai import AsyncOpenAI

from app.core.modules import Module
from config import Settings

router = Router(name="mail")


class MailModule(Module):
    name = "mail"

    def __init__(self, settings: Settings):
        super().__init__(settings)
        self.client: Optional[AsyncOpenAI] = None
        if settings.openai_api_key:
            self.client = AsyncOpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
            )

    def initialize(self, dispatcher: Dispatcher) -> None:
        dispatcher.include_router(router)

    async def process(self, user_id: int, message: str) -> str:
        return "Я могу получать почту и резюмировать письма. Используйте /mail для проверки."

    def get_capabilities(self):
        return ["fetch_mail", "analyze_mail"]

    async def _analyze(self, mail: EmailMessage) -> str:
        subject = mail.get("Subject", "(без темы)")
        sender = mail.get("From", "(неизвестно)")
        body = mail.get_payload(decode=True) or b""
        text = body.decode(errors="ignore")
        if not self.client:
            return f"Письмо от {sender} с темой '{subject}'."
        response = await self.client.chat.completions.create(
            model=self.settings.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": "Ты помощник, который кратко классифицирует и выделяет ключевое из письма",
                },
                {
                    "role": "user",
                    "content": f"Тема: {subject}\nОтправитель: {sender}\nТекст: {text[:4000]}",
                },
            ],
        )
        return response.choices[0].message.content or "Не удалось проанализировать письмо"


def _fetch_imap(settings: Settings, limit: int = 1) -> List[EmailMessage]:
    if not settings.mail_host or not settings.mail_username or not settings.mail_password:
        return []
    mails: List[EmailMessage] = []
    with imaplib.IMAP4_SSL(settings.mail_host, settings.mail_port) as client:
        client.login(settings.mail_username, settings.mail_password)
        client.select("INBOX")
        _, data = client.search(None, "ALL")
        ids = data[0].split()[-limit:]
        for uid in ids:
            _, msg_data = client.fetch(uid, "(RFC822)")
            raw = msg_data[0][1]
            mails.append(email.message_from_bytes(raw))
    return mails


def _fetch_pop3(settings: Settings, limit: int = 1) -> List[EmailMessage]:
    if not settings.mail_host or not settings.mail_username or not settings.mail_password:
        return []
    mails: List[EmailMessage] = []
    with poplib.POP3_SSL(settings.mail_host, settings.mail_port) as client:
        client.user(settings.mail_username)
        client.pass_(settings.mail_password)
        total, _ = client.stat()
        for idx in range(max(1, total - limit + 1), total + 1):
            response, lines, octets = client.retr(idx)
            raw = b"\n".join(lines)
            mails.append(email.message_from_bytes(raw))
    return mails


@router.message(Command("mail"))
async def check_mail(message: Message):
    settings: Settings = message.conf.get("settings")  # type: ignore[attr-defined]
    module: MailModule = message.conf.get("registry").get_module("mail")  # type: ignore[attr-defined]

    fetcher = _fetch_imap if settings.mail_protocol.lower() == "imap" else _fetch_pop3
    mails = await message.bot.loop.run_in_executor(None, fetcher, settings, 1)
    if not mails:
        await message.answer("Нет писем или не настроено соединение с почтой")
        return
    summary = await module._analyze(mails[0])
    await message.answer(summary)

