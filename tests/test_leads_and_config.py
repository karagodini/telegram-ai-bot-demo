from __future__ import annotations

import pytest
from pydantic import ValidationError

from bot.config import Settings, is_local_base_url
from bot.knowledge.faq import FaqIndex
from bot.providers.factory import build_provider
from bot.services.leads import (
    Lead,
    format_lead,
    mask_phone,
    normalize_phone,
    validate_name,
    validate_task,
)

FAQ = """
## Доставка
keywords: доставка

Доставка по городу занимает один день.
"""


def _settings(**overrides: object) -> Settings:
    payload: dict[str, object] = {"bot_token": "1:test", "ai_provider": "stub"}
    payload.update(overrides)
    return Settings(_env_file=None, **payload)  # type: ignore[arg-type]


def test_phone_name_and_task_validation() -> None:
    assert normalize_phone("+7 (999) 123-45-67") == "+79991234567"
    assert normalize_phone("8 999 123 45 67") == "+79991234567"
    assert normalize_phone("9991234567") == "+79991234567"
    assert normalize_phone("123") is None
    assert normalize_phone("+1 202 555 0147") is None
    assert normalize_phone("0001234567") is None

    assert validate_name("  Анна-Мария  ") == "Анна-Мария"
    assert validate_name("Иван Петров") == "Иван Петров"
    assert validate_name("А") is None
    assert validate_name("Анна 123") is None

    assert validate_task("  Покрасить стены в двушке ") == "Покрасить стены в двушке"
    assert validate_task("ок") is None


def test_lead_message_masks_phone_in_logs_helper() -> None:
    lead = Lead(
        name="Анна",
        phone="+79991234567",
        task="Косметический ремонт студии",
        chat_id=42,
        username="anna",
    )
    text = format_lead(lead)
    assert "Анна" in text
    assert "+79991234567" in text
    assert "@anna" in text
    assert mask_phone(lead.phone) == "+7***4567"
    assert mask_phone(lead.phone) not in text


def test_settings_reject_unknown_provider_and_blank_manager() -> None:
    settings = _settings(manager_chat_id="", openai_api_key="  ")
    assert settings.manager_chat_id is None
    assert settings.openai_api_key is None
    with pytest.raises(ValidationError):
        _settings(ai_provider="huggingface")


def test_factory_stub_and_missing_key() -> None:
    faq = FaqIndex.from_markdown(FAQ)
    assert build_provider(_settings(), faq).name == "stub"

    remote = _settings(
        ai_provider="openai_compatible",
        openai_api_key=None,
        openai_base_url="https://openrouter.ai/api/v1",
    )
    assert build_provider(remote, faq).name == "stub"

    local = _settings(
        ai_provider="openai_compatible",
        openai_api_key=None,
        openai_base_url="http://127.0.0.1:11434/v1",
        openai_model="llama3.2",
    )
    assert is_local_base_url(local.openai_base_url)
    assert is_local_base_url("http://host.docker.internal:11434/v1")
    assert not is_local_base_url("https://evil.example/127.0.0.1")
    assert build_provider(local, faq).name == "openai_compatible+fallback:stub"

    cloud = _settings(
        ai_provider="openai_compatible",
        openai_api_key="sk-test",
        openai_base_url="https://api.groq.com/openai/v1",
        openai_model="llama-3.3-70b-versatile",
    )
    assert build_provider(cloud, faq).name == "openai_compatible+fallback:stub"
