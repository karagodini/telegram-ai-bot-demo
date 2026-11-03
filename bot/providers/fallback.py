"""Если основной провайдер упал, отвечаем заглушкой."""

from __future__ import annotations

import logging
from collections.abc import Sequence

from bot.providers.base import ChatMessage, LLMProvider, ProviderError

logger = logging.getLogger(__name__)


class FallbackProvider:
    def __init__(self, primary: LLMProvider, fallback: LLMProvider) -> None:
        self._primary = primary
        self._fallback = fallback
        self.name = f"{primary.name}+fallback:{fallback.name}"

    async def complete(self, messages: Sequence[ChatMessage]) -> str:
        try:
            return await self._primary.complete(messages)
        except ProviderError as exc:
            logger.warning(
                "провайдер %s недоступен (%s), отвечаем через %s",
                self._primary.name,
                exc,
                self._fallback.name,
            )
            return await self._fallback.complete(messages)
