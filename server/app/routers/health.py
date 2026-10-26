"""F9 health endpoint. Reports which providers are configured, so a glance
tells you whether the demo will run on Groq or needs the cache."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session, text

from app.core.config import settings
from app.core.db import get_session

router = APIRouter(prefix="/api", tags=["health"])


class HealthOut(BaseModel):
    status: str
    database: bool
    groq_configured: bool
    gemini_configured: bool
    llm_cache_enabled: bool
    demo_tamper_enabled: bool


@router.get("/health", response_model=HealthOut)
def health(session: Session = Depends(get_session)) -> HealthOut:
    try:
        session.exec(text("SELECT 1"))
        database = True
    except Exception:
        database = False

    return HealthOut(
        status="ok" if database else "degraded",
        database=database,
        groq_configured=settings.groq_configured,
        gemini_configured=settings.gemini_configured,
        llm_cache_enabled=settings.llm_cache_enabled,
        demo_tamper_enabled=settings.demo_tamper_enabled,
    )
