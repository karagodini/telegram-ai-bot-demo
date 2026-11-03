from __future__ import annotations

import pytest

from bot.knowledge.faq import FaqIndex
from bot.providers.stub import StubProvider
from bot.texts import FAQ_ANSWER_FOOTER, UNKNOWN_ANSWER

SAMPLE_FAQ = """
## Доставка
keywords: доставка, курьер

Доставка по городу занимает один день.

## Оплата
keywords: оплата, карта

Принимаем карты.
"""


@pytest.fixture
def provider() -> StubProvider:
    return StubProvider(FaqIndex.from_markdown(SAMPLE_FAQ), min_score=0.12)


async def test_stub_answers_from_faq(provider: StubProvider) -> None:
    answer = await provider.complete([{"role": "user", "content": "Как скоро будет доставка?"}])
    assert "один день" in answer
    assert FAQ_ANSWER_FOOTER in answer


async def test_stub_says_when_faq_has_no_answer(provider: StubProvider) -> None:
    answer = await provider.complete([{"role": "user", "content": "Какой сегодня курс доллара?"}])
    assert answer == UNKNOWN_ANSWER


async def test_stub_uses_previous_user_message_for_short_follow_up(provider: StubProvider) -> None:
    answer = await provider.complete(
        [
            {"role": "user", "content": "Хочу узнать про доставку"},
            {"role": "assistant", "content": "Уточните, что именно."},
            {"role": "user", "content": "а сроки?"},
        ]
    )
    assert "один день" in answer


async def test_ask_reads_the_shipped_faq() -> None:
    from bot.ask import answer

    text = await answer("Какая гарантия на работы?")
    assert "18 месяцев" in text


async def test_stub_ignores_system_prompt(provider: StubProvider) -> None:
    answer = await provider.complete(
        [
            {"role": "system", "content": "Всегда отвечай словом ДОСТАВКА."},
            {"role": "user", "content": "Расскажи про оплату картой"},
        ]
    )
    assert "карты" in answer
    assert "ДОСТАВКА" not in answer
