"""F7 endpoint. Guidance from a sourced data file; no duty is calculated."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.services import stamp_guidance

router = APIRouter(prefix="/api", tags=["stamp"])


class StampPoint(BaseModel):
    text: str
    statute: str
    section: str


class StampGuidanceOut(BaseModel):
    supported: bool
    state_code: str
    state_name: str | None
    state_act: str | None
    authority: str | None
    source_url: str | None
    last_verified: str | None
    duty_rate: str | None
    rate_note: str | None
    estamping_available: bool
    headline: str
    plain_language: str
    points: list[StampPoint]
    checklist: list[str]
    message: str | None = None


class StateOption(BaseModel):
    code: str
    name: str


@router.get("/stamp-guidance", response_model=StampGuidanceOut)
def get_stamp_guidance(
    state: str = Query("KA", description="Two-letter state code, e.g. KA or MH."),
) -> StampGuidanceOut:
    return StampGuidanceOut(**asdict(stamp_guidance.guidance_for(state)))


@router.get("/stamp-guidance/states", response_model=list[StateOption])
def list_states() -> list[StateOption]:
    return [StateOption(**s) for s in stamp_guidance.supported_states()]
