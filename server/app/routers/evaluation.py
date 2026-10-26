"""P1-5: in-app evaluation page."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.services import eval_report
from app.services.llm_service import PROMPT_VERSION

router = APIRouter(prefix="/api/eval", tags=["evaluation"])


class CheckRowOut(BaseModel):
    id: str
    scenario: str
    passed: bool
    detail: str
    skipped: bool


class CheckGroupOut(BaseModel):
    title: str
    description: str
    passed: int
    total: int
    rows: list[CheckRowOut]


class AiRowOut(BaseModel):
    id: str
    scenario: str
    expected: str
    actual: str
    passed: bool
    known_failure: bool
    note: str
    dropped_ungrounded: int = 0


class AiRunOut(BaseModel):
    ran_at: str
    model: str | None
    prompt_version: str | None
    current_prompt_version: str
    stale: bool  # prompt changed since that run
    fresh: bool
    passed: int
    total: int
    dropped_ungrounded: int
    rows: list[AiRowOut]


class EvalOut(BaseModel):
    fixtures_found: bool
    live: list[CheckGroupOut]
    ai: AiRunOut | None  # None: run_eval has not been run here yet
    how_to_run: str = "docker compose exec server python -m tests.run_eval"


def _group(title: str, description: str, rows: list[eval_report.CheckRow]) -> CheckGroupOut:
    counted = [r for r in rows if not r.skipped]
    return CheckGroupOut(
        title=title,
        description=description,
        passed=sum(r.passed for r in counted),
        total=len(counted),
        rows=[CheckRowOut(id=r.id, scenario=r.scenario, passed=r.passed, detail=r.detail, skipped=r.skipped) for r in rows],
    )


@router.get("", response_model=EvalOut)
def evaluation() -> EvalOut:
    live = eval_report.run_live_checks()
    last = eval_report.last_ai_run()
    ai = None
    if last is not None:
        ai = AiRunOut(
            ran_at=str(last.get("ran_at")),
            model=last.get("model"),
            prompt_version=last.get("prompt_version"),
            current_prompt_version=PROMPT_VERSION,
            stale=last.get("prompt_version") != PROMPT_VERSION,
            fresh=bool(last.get("fresh")),
            passed=int(last.get("passed", 0)),
            total=int(last.get("total", 0)),
            dropped_ungrounded=int(last.get("dropped_ungrounded", 0)),
            rows=[AiRowOut(**r) for r in last.get("rows", [])],
        )
    return EvalOut(
        fixtures_found=live.fixtures_found,
        live=[
            _group("Chat reading", "Each labelled chat parsed live: participants, message count, date order and attachments match the label.", live.parser),
            _group("Bad files rejected", "Broken or wrong inputs fail with a clear message instead of a crash.", live.invalid),
            _group("Rules only, no AI", "Every labelled chat through patterns, grounding, the s.62 rule and the checklist with the model switched off: the floor if the AI returns nothing. The AI only adds to this.", live.rules),
            _group("Identifiers hidden", "The exact transcript sent to the model contains no phone, PAN, Aadhaar, GSTIN, email or UPI ID.", live.masking),
        ],
        ai=ai,
    )
