from __future__ import annotations

from pathlib import Path

import pytest

from bot.knowledge.faq import FaqIndex, build_search_query, tokenize

ROOT = Path(__file__).resolve().parents[1]

SAMPLE_FAQ = """
# Тестовая база

## Доставка
keywords: доставка, курьер

Доставка по городу занимает один день.

## Оплата
keywords: оплата, карта, счет

Принимаем карты и безналичный счет.

## Гарантия
keywords: гарантия, возврат

Гарантия на работу — двенадцать месяцев.
"""


@pytest.fixture
def index() -> FaqIndex:
    return FaqIndex.from_markdown(SAMPLE_FAQ)


def test_tokenize_joins_word_forms() -> None:
    assert tokenize("Доставку доставки") == ["доставк", "доставк"]
    assert tokenize("Привет!") == []


def test_search_ranks_relevant_section_first(index: FaqIndex) -> None:
    hits = index.search("Как работает доставка курьером?")
    assert hits
    assert hits[0].entry.title == "Доставка"
    assert hits[0].score > hits[-1].score or len(hits) == 1


def test_search_finds_payment_by_card_word(index: FaqIndex) -> None:
    hit = index.best("Можно ли оплатить картой?", min_score=0.1)
    assert hit is not None
    assert hit.entry.title == "Оплата"


def test_unknown_query_stays_below_threshold(index: FaqIndex) -> None:
    assert index.best("Какой курс биткоина сегодня?", min_score=0.18) is None
    assert index.search("Привет!") == []


def test_short_follow_up_uses_previous_question(index: FaqIndex) -> None:
    query = build_search_query(["Расскажите про доставку по городу", "а сроки?"])
    assert "доставк" in " ".join(tokenize(query))
    hit = index.best(query, min_score=0.1)
    assert hit is not None
    assert hit.entry.title == "Доставка"


def test_empty_markdown_is_rejected() -> None:
    with pytest.raises(ValueError):
        FaqIndex.from_markdown("# Только заголовок\n\nБез секций.")


def test_sample_business_faq_answers_typical_questions() -> None:
    business = FaqIndex.from_path(ROOT / "data" / "faq.md")
    price = business.best("Сколько стоит косметический ремонт квартиры?", min_score=0.12)
    warranty = business.best("Какая гарантия на работы?", min_score=0.12)
    contacts = business.best("Как с вами связаться и до скольки вы работаете?", min_score=0.12)
    assert price is not None and price.entry.title == "Стоимость ремонта"
    assert warranty is not None and warranty.entry.title == "Гарантия"
    assert contacts is not None and contacts.entry.title == "Контакты"
    assert business.best("Какой курс доллара к рублю?", min_score=0.18) is None
