"""Заглушка: ответ берётся из FAQ, внешний API не нужен."""

from __future__ import annotations

import logging
from collections.abc import Sequence

from bot.knowledge.faq import FaqIndex, build_search_query
from bot.providers.base import ChatMessage
from bot.texts import UNKNOWN_ANSWER, format_faq_answer

logger = logging.getLogger(__name__)


class StubProvider:
    name = "stub"

    def __init__(self, faq: FaqIndex, min_score: float = 0.18) -> None:
        self._faq = faq
        self._min_score = min_score

    async def complete(self, messages: Sequence[ChatMessage]) -> str:
        user_texts = [message["content"] for message in messages if message["role"] == "user"]
        query = build_search_query(user_texts)
        hit = self._faq.best(query, min_score=self._min_score)
        if hit is None:
            logger.debug("stub miss, tokens=%s", len(query.split()))
            return UNKNOWN_ANSWER
        logger.debug("stub hit title=%s score=%.3f", hit.entry.title, hit.score)
        return format_faq_answer(hit.entry.body)
