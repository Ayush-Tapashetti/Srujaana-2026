"""Configuration from the environment.

No settings library (TECH_STACK D12): nine variables do not justify one.
Everything is read once at import so a missing or malformed value fails at
startup with a clear message, rather than inside an LLM call later.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigError(RuntimeError):
    """A required environment variable is missing or unusable."""


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ConfigError(
            f"{name} is not set. Copy .env.example to .env and fill it in."
        )
    return value


def _optional(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _flag(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a whole number, got {raw!r}") from exc


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str

    groq_api_key: str
    groq_model: str
    gemini_api_key: str
    gemini_model: str

    llm_cache_enabled: bool
    demo_tamper_enabled: bool
    confirm_link_ttl_hours: int
    max_upload_bytes: int


    # Fixed limits, not environment-driven.
    max_messages: int = 5_000
    llm_timeout_seconds: float = 30.0

    @property
    def groq_configured(self) -> bool:
        return bool(self.groq_api_key and self.groq_model)

    @property
    def gemini_configured(self) -> bool:
        return bool(self.gemini_api_key and self.gemini_model)


def load_settings() -> Settings:
    return Settings(
        database_url=_required("DATABASE_URL"),
        # LLM keys are optional at startup: F1 (parse, mask, hash) must work
        # before any key exists, so the server still boots without them.
        groq_api_key=_optional("GROQ_API_KEY"),
        groq_model=_optional("GROQ_MODEL"),
        gemini_api_key=_optional("GEMINI_API_KEY"),
        gemini_model=_optional("GEMINI_MODEL"),
        llm_cache_enabled=_flag("LLM_CACHE_ENABLED", True),
        demo_tamper_enabled=_flag("DEMO_TAMPER_ENABLED", False),
        confirm_link_ttl_hours=_int("CONFIRM_LINK_TTL_HOURS", 72),
        max_upload_bytes=_int("MAX_UPLOAD_MB", 2) * 1024 * 1024,
    )


settings = load_settings()
