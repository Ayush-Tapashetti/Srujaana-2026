"""F2 and F3 endpoints: run extraction, read the result."""

from __future__ import annotations

import logging
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.core.lookup import get_conversation_or_404
from app.core.db import get_session
from app.models.analysis import Analysis, ExtractedTerm, Flag, Severity, TermStatus, TermType
from app.models.conversation import Message
from app.models.evidence import EventType
from app.schemas.analysis import AnalysisOut, FlagOut, MsmeCheckOut, RevisionOut, TermOut
from app.services import checklist_engine, extractor
from app.services.evidence_chain import append_event
from app.services.llm_service import PROMPT_VERSION, LlmUnavailable

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/conversations", tags=["analysis"])


def _messages(session: Session, conversation_id: int) -> list[Message]:
    return list(
        session.exec(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.index)
        ).all()
    )


def _latest_analysis(session: Session, conversation_id: int) -> Analysis | None:
    return session.exec(
        select(Analysis)
        .where(Analysis.conversation_id == conversation_id)
        .order_by(Analysis.id.desc())
        .limit(1)
    ).first()


def _flag_out(f: Flag | checklist_engine.FlagSpec) -> FlagOut:
    return FlagOut(
        term_type=f.term_type,
        severity=f.severity,
        title=f.title,
        why_it_matters=f.why_it_matters,
        statute=f.statute,
        section=f.section,
        statute_gist=f.statute_gist,
        suggested_question=f.suggested_question,
        source_message_ids=f.source_message_ids,
    )


def _to_out(session: Session, analysis: Analysis) -> AnalysisOut:
    terms = list(
        session.exec(
            select(ExtractedTerm).where(ExtractedTerm.analysis_id == analysis.id)
        ).all()
    )
    flags = list(
        session.exec(select(Flag).where(Flag.analysis_id == analysis.id)).all()
    )

    missing = [f.term_type for f in flags if f.severity is Severity.RED]
    messages = _messages(session, analysis.conversation_id)

    def response_index(t: ExtractedTerm) -> int | None:
        if not t.revision_history or not t.source_message_ids:
            return None
        return extractor.judged_reply_index(messages, t.source_message_ids)

    return AnalysisOut(
        id=analysis.id,
        conversation_id=analysis.conversation_id,
        created_at=analysis.created_at,
        readiness=analysis.readiness,
        can_send=analysis.readiness is not Severity.RED,
        missing_critical=sorted(set(missing), key=lambda t: t.value),
        terms=[
            TermOut(
                type=t.type,
                value=t.value,
                status=t.status,
                confidence=t.confidence,
                source_message_ids=t.source_message_ids,
                revision_state=t.revision_state,
                revision_history=[
                    RevisionOut(**r) for r in (t.revision_history or [])
                ],
                response_message_index=response_index(t),
            )
            for t in terms
        ],
        flags=[_flag_out(f) for f in flags],
        model_used=analysis.model_used,
        prompt_version=analysis.prompt_version,
        from_cache=analysis.from_cache,
    )


@router.post("/{conversation_id}/extract", response_model=AnalysisOut)
def run_extraction(
    conversation_id: int,
    force: bool = Query(
        False, description="Re-run even if an analysis already exists."
    ),
    session: Session = Depends(get_session),
) -> AnalysisOut:
    get_conversation_or_404(session, conversation_id)

    if not force:
        existing = _latest_analysis(session, conversation_id)
        if existing is not None:
            return _to_out(session, existing)

    messages = _messages(session, conversation_id)
    if not messages:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "This conversation has no messages."
        )

    try:
        result = extractor.extract(session, messages)
    except LlmUnavailable as exc:
        # 503, not 500: the pipeline is fine, the provider is not. The UI
        # tells the user to try a cached sample rather than showing a crash.
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc

    checklist = checklist_engine.evaluate(result.terms)

    analysis = Analysis(
        conversation_id=conversation_id,
        model_used=result.model_used,
        prompt_version=PROMPT_VERSION,
        from_cache=result.from_cache,
        readiness=checklist.readiness,
    )
    session.add(analysis)
    session.flush()

    for term in result.terms:
        session.add(
            ExtractedTerm(
                analysis_id=analysis.id,
                type=term.type,
                value=term.value,
                status=term.status,
                confidence=term.confidence,
                source_message_ids=term.source_message_ids,
                revision_state=term.revision_state,
                revision_history=[
                    {"value": r.value, "source_message_ids": r.source_message_ids}
                    for r in term.revision_history
                ],
                source_verified=True,  # ungrounded mentions never get this far
            )
        )

    for spec in checklist.flags:
        session.add(
            Flag(
                analysis_id=analysis.id,
                term_type=spec.term_type,
                severity=spec.severity,
                title=spec.title,
                why_it_matters=spec.why_it_matters,
                statute=spec.statute,
                section=spec.section,
                statute_gist=spec.statute_gist,
                suggested_question=spec.suggested_question,
                source_message_ids=spec.source_message_ids,
            )
        )

    append_event(
        session,
        conversation_id=conversation_id,
        event_type=EventType.EXTRACTION,
        payload={
            "analysis_id": analysis.id,
            "model": result.model_used,
            "prompt_version": PROMPT_VERSION,
            "from_cache": result.from_cache,
            "term_count": len(result.terms),
            "readiness": checklist.readiness.value,
            "dropped_ungrounded": len(result.dropped_ungrounded),
            "filled_by_rules": result.filled_by_rules,
        },
    )

    session.commit()
    session.refresh(analysis)

    out = _to_out(session, analysis)
    out.dropped_ungrounded = result.dropped_ungrounded
    out.filled_by_rules = result.filled_by_rules
    return out


@router.get("/{conversation_id}/analysis", response_model=AnalysisOut)
def read_analysis(
    conversation_id: int,
    session: Session = Depends(get_session),
) -> AnalysisOut:
    get_conversation_or_404(session, conversation_id)

    analysis = _latest_analysis(session, conversation_id)
    if analysis is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "This chat has not been analysed yet. Run extraction first.",
        )
    return _to_out(session, analysis)


class SupplierAnswer(str, Enum):
    YES = "yes"
    NO = "no"
    UNSURE = "unsure"


@router.get("/{conversation_id}/msme-check", response_model=MsmeCheckOut)
def msme_check(
    conversation_id: int,
    supplier_is_micro_or_small: SupplierAnswer = Query(
        ..., description="Is the supplier registered as micro or small (Udyam)?"
    ),
    session: Session = Depends(get_session),
) -> MsmeCheckOut:
    """P1-2. Stateless: the answer is not stored and readiness is unchanged.

    Whether the supplier is registered is a fact outside the chat, so it is
    asked, never guessed, and only a "yes" produces the s.15 flag.
    """
    get_conversation_or_404(session, conversation_id)
    analysis = _latest_analysis(session, conversation_id)
    if analysis is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "This chat has not been analysed yet. Run extraction first.",
        )
    payment = session.exec(
        select(ExtractedTerm).where(
            ExtractedTerm.analysis_id == analysis.id,
            ExtractedTerm.type == TermType.PAYMENT_DUE,
        )
    ).first()
    value = payment.value if payment is not None else None
    days = checklist_engine.payment_period_days(value) if value else None
    exceeds = days is not None and days > checklist_engine.MSME_MAX_DAYS

    flag = None
    if supplier_is_micro_or_small is SupplierAnswer.YES and payment is not None:
        spec = checklist_engine.msme_payment_warning([payment])  # type: ignore[list-item]
        flag = _flag_out(spec) if spec is not None else None

    if value is None:
        note = "No payment period was found in the chat, so there is nothing to check."
    elif days is None:
        note = "The payment term does not state a number of days, so the 45-day limit cannot be checked."
    elif supplier_is_micro_or_small is SupplierAnswer.NO:
        note = "The 45-day limit in MSMED Act s.15 protects micro and small suppliers only, so it does not apply here."
    elif supplier_is_micro_or_small is SupplierAnswer.UNSURE:
        note = (
            "Ask the supplier for their Udyam registration number. If they are micro or small, "
            + ("this term is longer than the 45 days the law allows." if exceeds else "this term is within the 45-day limit.")
        )
    elif exceeds:
        note = (
            "If paid late, s.16 makes the buyer liable for compound interest with monthly rests "
            "at three times the RBI bank rate. This is advisory and does not change readiness."
        )
    else:
        note = "This payment term is within the 45-day limit."

    return MsmeCheckOut(
        answer=supplier_is_micro_or_small.value,
        payment_term=value,
        period_days=days,
        limit_days=checklist_engine.MSME_MAX_DAYS,
        exceeds_limit=exceeds,
        flag=flag,
        note=note,
    )
