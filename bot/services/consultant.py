"""Склеивает историю, фрагменты FAQ и выбранный провайдер."""

from __future__ import annotations

from collections.abc import Sequence

from bot.knowledge.faq import FaqIndex, build_search_query
from bot.memory import DialogMemory
from bot.providers.base import ChatMessage, LLMProvider

_TELEGRAM_LIMIT = 4000


class Consultant:
    def __init__(
        self,
        *,
        provider: LLMProvider,
        faq: FaqIndex,
        memory: DialogMemory,
        system_prompt: str,
        context_limit: int = 3,
    ) -> None:
        self._provider = provider
        self._faq = faq
        self._memory = memory
        self._system_prompt = system_prompt.strip()
        self._context_limit = context_limit

    async def reply(self, chat_id: int, user_text: str) -> str:
        text = user_text.strip()
        history = self._memory.get(chat_id)
        messages: list[ChatMessage] = [
            {"role": "system", "content": self._system_message(text, history)},
            *history,
            {"role": "user", "content": text},
        ]
        answer = _clip(await self._provider.complete(messages))
        self._memory.add(chat_id, "user", text)
        self._memory.add(chat_id, "assistant", answer)
        return answer

    def _system_message(self, user_text: str, history: Sequence[ChatMessage]) -> str:
        previous = [message["content"] for message in history if message["role"] == "user"]
        query = build_search_query([*previous, user_text])
        hits = self._faq.search(query, limit=self._context_limit)
        if not hits:
            context = "Подходящих фрагментов базы знаний нет. Не выдумывай факты о компании."
        else:
            blocks = [
                f"[{index}] {hit.entry.title}\n{hit.entry.body}"
                for index, hit in enumerate(hits, start=1)
            ]
            context = "Фрагменты базы знаний:\n\n" + "\n\n".join(blocks)
        return f"{self._system_prompt}\n\n{context}"


def _clip(text: str, limit: int = _TELEGRAM_LIMIT) -> str:
    cleaned = text.strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1] + "…"
