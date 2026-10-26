"""F2 and F3 response shapes. Mirror in client/src/types/analysis.ts."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.analysis import RevisionState, Severity, TermStatus, TermType


class RevisionOut(BaseModel):
    value: str
    source_message_ids: list[int]


class TermOut(BaseModel):
    type: TermType
    value: str | None
    status: TermStatus
    confidence: float
    source_message_ids: list[int]
    revision_state: RevisionState
    revision_history: list[RevisionOut] = Field(default_factory=list)
    # P1-3: the other party's first text reply after the active value, the
    # one message the s.62 rule judged. None when nobody replied, or when
    # there was no revision. Computed at read time, not stored.
    response_message_index: int | None = None


class FlagOut(BaseModel):
    term_type: TermType
    severity: Severity
    title: str
    why_it_matters: str

    # Rendered inline on the flag, not buried in the README. This is the
    # difference between "we used the Contract Act" and showing the judge
    # the section the flag rests on.
    statute: str
    section: str
    statute_gist: str

    suggested_question: str | None
    source_message_ids: list[int]


class AnalysisOut(BaseModel):
    id: int
    conversation_id: int
    created_at: datetime

    readiness: Severity
    can_send: bool
    missing_critical: list[TermType]

    terms: list[TermOut]
    flags: list[FlagOut]

    model_used: str
    prompt_version: str
    from_cache: bool

    # Mentions the model produced whose value was not present in the
    # messages they cited. Surfaced rather than hidden: it is the evidence
    # that the grounding check is doing something.
    dropped_ungrounded: list[dict] = Field(default_factory=list)
    # Term types the model returned nothing for, found by the deterministic
    # patterns instead (shown on a fresh run; also in the evidence event).
    filled_by_rules: list[str] = Field(default_factory=list)


class MsmeCheckOut(BaseModel):
    """P1-2. Advisory only: never changes readiness or can_send."""

    answer: str  # "yes" | "no" | "unsure"
    payment_term: str | None
    period_days: int | None
    limit_days: int
    exceeds_limit: bool
    flag: FlagOut | None  # only when answer == "yes" and the term exceeds
    note: str
