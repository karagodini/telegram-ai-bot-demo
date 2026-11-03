"""Общий контракт провайдера ответов."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal, Protocol, TypedDict


class ChatMessage(TypedDict):
    role: Literal["system", "user", "assistant"]
    content: str


class ProviderError(Exception):
    """Ошибка внешнего API. Слой выше может ответить заглушкой."""


class LLMProvider(Protocol):
    name: str

    async def complete(self, messages: Sequence[ChatMessage]) -> str:
        """Возвращает текст ответа ассистента."""
