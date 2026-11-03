"""Последний рубеж: ошибка хендлера не должна ронять polling."""

from __future__ import annotations

import logging

from aiogram.exceptions import TelegramAPIError
from aiogram.types import ErrorEvent, Message

from bot.texts import GENERIC_ERROR

logger = logging.getLogger(__name__)


async def on_error(event: ErrorEvent) -> None:
    logger.exception("необработанная ошибка апдейта", exc_info=event.exception)
    message = event.update.message
    if not isinstance(message, Message):
        return
    try:
        await message.answer(GENERIC_ERROR)
    except TelegramAPIError:
        logger.warning("не удалось отправить сообщение об ошибке")
