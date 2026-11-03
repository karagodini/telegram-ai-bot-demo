"""Прогон команд, диалога и заявки без сети Telegram."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

from aiogram import Bot, Dispatcher, Router
from aiogram.client.session.base import BaseSession
from aiogram.enums import ChatType
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.methods import SendChatAction, SendMessage, TelegramMethod
from aiogram.methods.base import TelegramType
from aiogram.types import Chat, Message, Update, User

from bot.config import Settings
from bot.handlers import chat, commands, lead
from bot.handlers.errors import on_error
from bot.knowledge.faq import FaqIndex
from bot.memory import DialogMemory
from bot.providers.factory import build_provider
from bot.services.consultant import Consultant
from bot.texts import (
    ASK_NAME,
    ASK_NAME_AGAIN,
    ASK_PHONE,
    ASK_PHONE_AGAIN,
    ASK_TASK,
    ASK_TASK_AGAIN,
    GENERIC_ERROR,
    LEAD_SENT,
    START,
    UNKNOWN_ANSWER,
)

MANAGER_ID = 555
USER_ID = 100


class MemorySession(BaseSession):
    def __init__(self) -> None:
        super().__init__()
        self.calls: list[TelegramMethod[Any]] = []

    async def close(self) -> None:
        return None

    async def make_request(
        self,
        bot: Bot,
        method: TelegramMethod[TelegramType],
        timeout: int | None = None,
    ) -> TelegramType:
        self.calls.append(method)
        if isinstance(method, SendMessage):
            return Message(
                message_id=len(self.calls),
                date=datetime.now(UTC),
                chat=Chat(id=int(method.chat_id), type=ChatType.PRIVATE),
                text=method.text,
            )
        if isinstance(method, SendChatAction):
            return True
        raise AssertionError(f"unexpected method {method}")

    async def stream_content(
        self,
        url: str,
        headers: dict[str, Any] | None = None,
        timeout: int = 30,
        chunk_size: int = 65536,
        raise_for_status: bool = True,
    ) -> AsyncGenerator[bytes, None]:
        yield b""


def _dispatcher(settings: Settings) -> tuple[Dispatcher, Bot, MemorySession]:
    faq = FaqIndex.from_path(settings.faq_path)
    memory = DialogMemory(max_messages=settings.history_limit)
    consultant = Consultant(
        provider=build_provider(settings, faq),
        faq=faq,
        memory=memory,
        system_prompt=settings.system_prompt_path.read_text(encoding="utf-8"),
    )
    session = MemorySession()
    bot = Bot(token="1:test", session=session)
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.include_router(commands.router)
    dispatcher.include_router(lead.router)
    dispatcher.include_router(chat.router)
    dispatcher.workflow_data.update(settings=settings, consultant=consultant, memory=memory)
    return dispatcher, bot, session


def _incoming(text: str, number: int) -> Update:
    return Update(
        update_id=number,
        message=Message(
            message_id=number,
            date=datetime.now(UTC),
            chat=Chat(id=USER_ID, type=ChatType.PRIVATE),
            from_user=User(id=USER_ID, is_bot=False, first_name="Анна", username="anna"),
            text=text,
        ),
    )


def _texts(session: MemorySession) -> list[tuple[int, str]]:
    return [
        (int(call.chat_id), call.text) for call in session.calls if isinstance(call, SendMessage)
    ]


async def test_dialog_and_lead_reach_the_manager() -> None:
    settings = Settings(
        _env_file=None,
        bot_token="1:test",
        ai_provider="stub",
        manager_chat_id=MANAGER_ID,
    )
    dispatcher, bot, session = _dispatcher(settings)

    steps = [
        "/start",
        "Сколько стоит косметический ремонт?",
        "Какой курс доллара?",
        "Оставить заявку",
        "А",
        "Анна",
        "123",
        "+7 (999) 123-45-67",
        "ок",
        "Покрасить стены в студии",
    ]
    for number, text in enumerate(steps, start=1):
        await dispatcher.feed_update(bot, _incoming(text, number))

    sent = _texts(session)
    user_replies = [text for chat_id, text in sent if chat_id == USER_ID]
    manager_replies = [text for chat_id, text in sent if chat_id == MANAGER_ID]

    assert user_replies[0] == START
    assert "9 000" in user_replies[1]
    assert user_replies[2] == UNKNOWN_ANSWER
    assert user_replies[3] == ASK_NAME
    assert user_replies[4] == ASK_NAME_AGAIN
    assert user_replies[5] == ASK_PHONE
    assert user_replies[6] == ASK_PHONE_AGAIN
    assert user_replies[7] == ASK_TASK
    assert user_replies[8] == ASK_TASK_AGAIN
    assert user_replies[9] == LEAD_SENT
    assert len(manager_replies) == 1
    assert "Анна" in manager_replies[0]
    assert "+79991234567" in manager_replies[0]
    assert "Покрасить стены в студии" in manager_replies[0]
    assert "@anna" in manager_replies[0]

    await bot.session.close()


async def test_handler_error_is_reported_to_the_user() -> None:
    session = MemorySession()
    bot = Bot(token="1:test", session=session)
    dispatcher = Dispatcher()
    router = Router()

    @router.message()
    async def boom(message: Message) -> None:
        raise RuntimeError(message.text)

    dispatcher.include_router(router)
    dispatcher.errors.register(on_error)
    await dispatcher.feed_update(bot, _incoming("привет", 1))

    assert _texts(session)[-1] == (USER_ID, GENERIC_ERROR)
    await bot.session.close()
