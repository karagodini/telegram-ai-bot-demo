"""Настройки из окружения и файла ``.env``."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Корень репозитория: bot/config.py -> bot -> корень.
# Так бот находит FAQ и .env независимо от того, из какой папки его запустили.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

ProviderName = Literal["stub", "openai_compatible"]
_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
_LOCAL_HOST_MARKERS = ("localhost", "127.0.0.1", "0.0.0.0", "host.docker.internal")


def _blank_to_none(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return value


class Settings(BaseSettings):
    """Все параметры бота. Обязателен только ``BOT_TOKEN``."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str = Field(min_length=1)
    manager_chat_id: int | None = None

    ai_provider: ProviderName = "stub"
    openai_api_key: str | None = None
    openai_base_url: str = "https://openrouter.ai/api/v1"
    openai_model: str = "openrouter/free"
    llm_timeout_seconds: float = Field(default=40, gt=0, le=180)

    history_limit: int = Field(default=12, ge=2, le=40)
    faq_min_score: float = Field(default=0.18, ge=0, le=1)
    faq_path: Path = Field(default_factory=lambda: PROJECT_ROOT / "data" / "faq.md")
    system_prompt_path: Path = Field(
        default_factory=lambda: PROJECT_ROOT / "prompts" / "system.txt"
    )
    log_level: str = "INFO"

    @field_validator("manager_chat_id", "openai_api_key", mode="before")
    @classmethod
    def empty_optional(cls, value: object) -> object:
        return _blank_to_none(value)

    @field_validator("ai_provider", mode="before")
    @classmethod
    def normalize_provider(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        normalized = value.strip().lower()
        if normalized not in ("stub", "openai_compatible"):
            raise ValueError("AI_PROVIDER должен быть stub или openai_compatible")
        return normalized

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        name = value.strip().upper()
        if name not in _LOG_LEVELS:
            allowed = ", ".join(sorted(_LOG_LEVELS))
            raise ValueError(f"LOG_LEVEL должен быть одним из: {allowed}")
        return name

    @field_validator("openai_base_url")
    @classmethod
    def strip_base_url(cls, value: str) -> str:
        return value.strip().rstrip("/")


def load_settings() -> Settings:
    return Settings()


def is_local_base_url(base_url: str) -> bool:
    """Локальный OpenAI-совместимый сервер (Ollama) можно звать без настоящего ключа.

    Смотрим только hostname, чтобы чужой адрес с этими словами в пути не прошёл.
    """
    host = (urlparse(base_url).hostname or "").lower()
    return host in _LOCAL_HOST_MARKERS


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        force=True,
    )
    # SDK сам по себе шумный: на INFO он печатает каждый HTTP-запрос.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
