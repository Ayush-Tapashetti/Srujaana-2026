"""Check that the AI model is reachable, before a demo depends on it.

    docker compose exec server python -m app.check_llm

Makes one tiny request (a few dozen tokens), bypassing the cache, and says
plainly whether the key and model work.
"""

from __future__ import annotations

import sys

from sqlmodel import Session

from app.core.config import settings
from app.core.db import create_db_and_tables, engine
from app.services.llm_service import LlmUnavailable, complete_json, parse_json_object


def main() -> int:
    print(f"Groq   key {'set' if settings.groq_api_key else 'MISSING'}, model: {settings.groq_model or 'MISSING'}")
    print(f"Gemini key {'set' if settings.gemini_api_key else 'not set'}, model: {settings.gemini_model or 'not set'}")

    if not (settings.groq_configured or settings.gemini_configured):
        print("\nNo model configured. Set GROQ_API_KEY and GROQ_MODEL in .env, then restart:")
        print("    docker compose up -d --force-recreate server")
        return 1

    create_db_and_tables()
    with Session(engine) as session:
        try:
            response = complete_json(
                session,
                system="You reply with JSON only.",
                prompt='Reply with exactly this JSON object: {"ok": true}',
                use_cache=False,
            )
        except LlmUnavailable as exc:
            print(f"\nFAILED. {exc}")
            print("Check the key, and that the model ID still exists at https://console.groq.com/docs/models")
            return 1

    try:
        parsed = parse_json_object(response.text)
    except ValueError:
        print(f"\nThe model answered, but not with JSON:\n{response.text[:300]}")
        print("Try a different GROQ_MODEL.")
        return 1

    print(f"\nOK. {response.provider.value} answered with model {response.model}: {parsed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
