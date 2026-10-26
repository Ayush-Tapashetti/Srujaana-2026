"""Provider routing, retry, and cache for the two LLM calls (F9, D13).

Design notes:

- The model is never trusted. Callers validate every response against a
  Pydantic schema; this module only guarantees "some text came back".
- Groq first for speed, Gemini as failover. Both SDKs are imported lazily
  so the server boots and F1 works with no keys configured at all.
- The cache key includes the prompt version, so editing a prompt
  invalidates old entries instead of silently serving answers produced by a
  different instruction.
- Cached responses are labelled as cached in the API, never hidden. The
  switch is LLM_CACHE_ENABLED, turned off for live judge drills.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from enum import Enum

from sqlmodel import Session, select

from app.core.config import settings
from app.models.llm_cache import LlmCacheEntry

logger = logging.getLogger(__name__)

#: Bump on any prompt change. Part of the cache key.
PROMPT_VERSION = "2026-10-25.2"  # .2: Hinglish guide + worked example in the extraction prompt


class Provider(str, Enum):
    GROQ = "groq"
    GEMINI = "gemini"
    CACHE = "cache"


class LlmUnavailable(RuntimeError):
    """No provider could answer. The caller turns this into a clear error
    for the user rather than a half-filled analysis."""


@dataclass(slots=True)
class LlmResponse:
    text: str
    model: str
    provider: Provider
    from_cache: bool = False


def cache_key(system: str, prompt: str, model: str) -> str:
    material = f"{PROMPT_VERSION}\x00{model}\x00{system}\x00{prompt}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _read_cache(session: Session, key: str) -> LlmCacheEntry | None:
    return session.exec(
        select(LlmCacheEntry).where(LlmCacheEntry.cache_key == key)
    ).first()


def _write_cache(session: Session, key: str, model: str, text: str) -> None:
    session.add(
        LlmCacheEntry(
            cache_key=key,
            model=model,
            prompt_version=PROMPT_VERSION,
            response_text=text,
        )
    )
    session.commit()


def _call_groq(system: str, prompt: str) -> str:
    from groq import Groq  # lazy: not needed to boot

    client = Groq(api_key=settings.groq_api_key, timeout=settings.llm_timeout_seconds)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]
    try:
        completion = client.chat.completions.create(
            model=settings.groq_model,
            messages=messages,
            temperature=0.0,
            response_format={"type": "json_object"},
        )
    except Exception as exc:  # noqa: BLE001
        # Not every Groq model accepts JSON mode. If this one rejects it, ask
        # again without it: the prompt already demands JSON, and
        # parse_json_object strips any code fences around the answer.
        if "response_format" not in str(exc) and "json" not in str(exc).lower():
            raise
        logger.info("Model rejected JSON mode, retrying without it: %s", exc)
        completion = client.chat.completions.create(
            model=settings.groq_model, messages=messages, temperature=0.0
        )
    return completion.choices[0].message.content or ""


def _call_gemini(system: str, prompt: str) -> str:
    from google import genai  # lazy: optional dependency, only needed for the Gemini fallback
    from google.genai import types

    client = genai.Client(api_key=settings.gemini_api_key)
    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system,
            temperature=0.0,
            response_mime_type="application/json",
        ),
    )
    return response.text or ""


def complete_json(
    session: Session,
    *,
    system: str,
    prompt: str,
    use_cache: bool | None = None,
) -> LlmResponse:
    """Ask for a JSON object. One retry per provider, then failover.

    Raises LlmUnavailable if nothing answers.
    """
    caching = settings.llm_cache_enabled if use_cache is None else use_cache

    providers: list[tuple[Provider, str, callable]] = []
    if settings.groq_configured:
        providers.append((Provider.GROQ, settings.groq_model, _call_groq))
    if settings.gemini_configured:
        providers.append((Provider.GEMINI, settings.gemini_model, _call_gemini))

    if not providers:
        raise LlmUnavailable(
            "No language model is configured. Set GROQ_API_KEY and GROQ_MODEL "
            "in .env, or use a cached sample chat."
        )

    # A cache hit on any configured model is good enough, and is what lets
    # the demo run with the network unplugged.
    if caching:
        for _, model, _ in providers:
            key = cache_key(system, prompt, model)
            hit = _read_cache(session, key)
            if hit is not None:
                return LlmResponse(
                    text=hit.response_text,
                    model=hit.model,
                    provider=Provider.CACHE,
                    from_cache=True,
                )

    errors: list[str] = []
    for provider, model, call in providers:
        for attempt in (1, 2):  # one retry, then move to the next provider
            try:
                text = call(system, prompt)
                if not text.strip():
                    raise ValueError("empty response")
                if caching:
                    _write_cache(session, cache_key(system, prompt, model), model, text)
                return LlmResponse(text=text, model=model, provider=provider)
            except Exception as exc:  # noqa: BLE001 - provider SDKs raise widely
                logger.warning(
                    "%s attempt %s failed: %s", provider.value, attempt, exc
                )
                if attempt == 2:
                    errors.append(f"{provider.value}: {exc}")

    raise LlmUnavailable(
        "The language model could not be reached. " + "; ".join(errors)
    )


def parse_json_object(text: str) -> dict:
    """Pull a JSON object out of a model response.

    Models occasionally wrap JSON in a code fence even when asked not to, so
    this strips fences and falls back to the outermost braces. It does NOT
    repair malformed JSON: a response that is not parseable must fail so the
    retry fires.
    """
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.rstrip().endswith("```"):
            cleaned = cleaned.rstrip()[:-3]
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start != -1 and end > start:
            return json.loads(cleaned[start : end + 1])
        raise
