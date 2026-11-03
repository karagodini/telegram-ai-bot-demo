"""Сборка провайдера по настройкам."""

from __future__ import annotations

import logging

from bot.config import Settings, is_local_base_url
from bot.knowledge.faq import FaqIndex
from bot.providers.base import LLMProvider
from bot.providers.fallback import FallbackProvider
from bot.providers.openai_compatible import OpenAICompatibleProvider
from bot.providers.stub import StubProvider

logger = logging.getLogger(__name__)


def build_provider(settings: Settings, faq: FaqIndex) -> LLMProvider:
    stub = StubProvider(faq, min_score=settings.faq_min_score)
    if settings.ai_provider == "stub":
        logger.info("провайдер ответов: stub")
        return stub

    api_key = settings.openai_api_key
    if not api_key:
        if is_local_base_url(settings.openai_base_url):
            # Ollama не проверяет ключ, но SDK требует непустую строку.
            api_key = "ollama"
        else:
            logger.warning("OPENAI_API_KEY пустой, остаюсь на заглушке")
            return stub

    primary = OpenAICompatibleProvider(
        api_key=api_key,
        base_url=settings.openai_base_url,
        model=settings.openai_model,
        timeout=settings.llm_timeout_seconds,
    )
    logger.info(
        "провайдер ответов: openai_compatible model=%s base_url=%s",
        settings.openai_model,
        settings.openai_base_url,
    )
    return FallbackProvider(primary, stub)
