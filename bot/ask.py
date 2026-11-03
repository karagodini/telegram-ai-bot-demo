"""Локальная проверка заглушки без Telegram и без ключей.

Пример:
    python -m bot.ask "Сколько стоит капитальный ремонт?"
"""

from __future__ import annotations

import asyncio
import sys

from bot.config import PROJECT_ROOT
from bot.knowledge.faq import FaqIndex
from bot.providers.stub import StubProvider


async def answer(question: str) -> str:
    faq = FaqIndex.from_path(PROJECT_ROOT / "data" / "faq.md")
    provider = StubProvider(faq)
    return await provider.complete([{"role": "user", "content": question}])


def main() -> None:
    if len(sys.argv) < 2:
        print('Использование: python -m bot.ask "ваш вопрос"', file=sys.stderr)
        raise SystemExit(2)
    question = " ".join(sys.argv[1:]).strip()
    print(asyncio.run(answer(question)))


if __name__ == "__main__":
    main()
