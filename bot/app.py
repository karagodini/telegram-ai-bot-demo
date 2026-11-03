"""Точка входа: читает настройки, собирает бота и запускает long polling."""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot import __version__
from bot.config import configure_logging, load_settings
from bot.handlers import chat, commands, lead
from bot.handlers.errors import on_error
from bot.knowledge.faq import FaqIndex
from bot.memory import DialogMemory
from bot.providers.factory import build_provider
from bot.services.consultant import Consultant

logger = logging.getLogger(__name__)


async def run() -> None:
    settings = load_settings()
    configure_logging(settings.log_level)

    faq = FaqIndex.from_path(settings.faq_path)
    prompt_path = settings.system_prompt_path
    if not prompt_path.is_file():
        raise FileNotFoundError(f"Системный промпт не найден: {prompt_path}")
    system_prompt = prompt_path.read_text(encoding="utf-8")

    provider = build_provider(settings, faq)
    memory = DialogMemory(max_messages=settings.history_limit)
    consultant = Consultant(
        provider=provider,
        faq=faq,
        memory=memory,
        system_prompt=system_prompt,
    )

    bot = Bot(token=settings.bot_token)
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.include_router(commands.router)
    dispatcher.include_router(lead.router)
    dispatcher.include_router(chat.router)
    dispatcher.errors.register(on_error)

    logger.info(
        "бот %s запущен, статей FAQ: %s, провайдер: %s",
        __version__,
        len(faq.entries),
        provider.name,
    )
    try:
        await dispatcher.start_polling(
            bot,
            settings=settings,
            consultant=consultant,
            memory=memory,
        )
    finally:
        # start_polling закрывает сессию сам. Повторный close ничего не делает,
        # зато сессия не останется открытой, если polling оборвался до своего finally.
        await bot.session.close()


def main() -> None:
    asyncio.run(run())
