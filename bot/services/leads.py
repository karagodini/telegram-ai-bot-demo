"""Проверка полей заявки. Без Telegram, чтобы это можно было тестировать отдельно."""

from __future__ import annotations

import re
from dataclasses import dataclass

_NAME_RE = re.compile(r"[A-Za-zА-Яа-яЁё][A-Za-zА-Яа-яЁё' -]{0,79}")


@dataclass(frozen=True)
class Lead:
    name: str
    phone: str
    task: str
    chat_id: int
    username: str | None


def validate_name(raw: str) -> str | None:
    name = " ".join(raw.split())
    if not 2 <= len(name) <= 80:
        return None
    if _NAME_RE.fullmatch(name) is None:
        return None
    return name


def normalize_phone(raw: str) -> str | None:
    """Приводит российский номер к ``+7XXXXXXXXXX`` или возвращает None."""
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 10:
        national = digits
    elif len(digits) == 11 and digits[0] in "78":
        national = digits[1:]
    else:
        return None
    # Код города или оператора не начинается с 0.
    if national[0] == "0":
        return None
    return "+7" + national


def validate_task(raw: str) -> str | None:
    text = " ".join(raw.split())
    if not 5 <= len(text) <= 1000:
        return None
    return text


def mask_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    if len(digits) < 6:
        return "***"
    return f"+{digits[0]}***{digits[-4:]}"


def format_lead(lead: Lead) -> str:
    username = f"@{lead.username}" if lead.username else "—"
    return (
        "Новая заявка из Telegram-бота\n\n"
        f"Имя: {lead.name}\n"
        f"Телефон: {lead.phone}\n"
        f"Задача: {lead.task}\n\n"
        f"Клиент: {username}\n"
        f"chat_id: {lead.chat_id}"
    )
