"""История диалога в памяти процесса.

Для одного polling-инстанса этого достаточно. Перезапуск бота или команда
/reset очищают контекст. Между чатами истории не смешиваются.
"""

from __future__ import annotations

from typing import Literal

from bot.providers.base import ChatMessage


class DialogMemory:
    def __init__(self, max_messages: int = 12) -> None:
        if max_messages < 2:
            raise ValueError("max_messages должен быть не меньше 2")
        self._max = max_messages
        self._store: dict[int, list[ChatMessage]] = {}

    def add(self, chat_id: int, role: Literal["user", "assistant"], content: str) -> None:
        bucket = self._store.setdefault(chat_id, [])
        bucket.append({"role": role, "content": content})
        extra = len(bucket) - self._max
        if extra > 0:
            del bucket[:extra]

    def get(self, chat_id: int) -> list[ChatMessage]:
        return list(self._store.get(chat_id, ()))

    def reset(self, chat_id: int) -> None:
        self._store.pop(chat_id, None)
