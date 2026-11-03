"""Клиент любого OpenAI-совместимого Chat Completions API.

Подходит для OpenRouter, Groq, локальной Ollama (``/v1``) и других шлюзов,
которые повторяют схему ``/chat/completions``.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from openai import APIError, AsyncOpenAI, OpenAIError

from bot.providers.base import ChatMessage, ProviderError

logger = logging.getLogger(__name__)


class OpenAICompatibleProvider:
    name = "openai_compatible"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout: float,
    ) -> None:
        self._model = model
        headers: dict[str, str] | None = None
        # OpenRouter просит эти заголовки для статистики приложений.
        # Другим шлюзам они не мешают, но на всякий случай шлём только туда.
        if "openrouter.ai" in base_url:
            headers = {
                "HTTP-Referer": "https://github.com/karagodini/telegram-ai-bot-demo",
                "X-Title": "Telegram AI consultant demo",
            }
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            default_headers=headers,
        )

    async def complete(self, messages: Sequence[ChatMessage]) -> str:
        payload: list[dict[str, str]] = [
            {"role": message["role"], "content": message["content"]} for message in messages
        ]
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=payload,  # type: ignore[arg-type]
                temperature=0.2,
                max_tokens=700,
            )
        except (APIError, OpenAIError, TimeoutError, OSError) as exc:
            raise ProviderError(f"{type(exc).__name__}: {exc}") from exc
        except Exception as exc:
            # httpx иногда поднимает ошибки соединения, которые не наследуют OpenAIError
            # (Ollama выключена, DNS, обрыв). Для бота это тоже повод уйти в заглушку.
            logger.debug("unexpected provider exception", exc_info=exc)
            raise ProviderError(f"{type(exc).__name__}: {exc}") from exc

        if not response.choices:
            raise ProviderError("модель не вернула вариантов ответа")
        content = response.choices[0].message.content
        if content is None or not content.strip():
            raise ProviderError("модель вернула пустой ответ")
        return content.strip()
