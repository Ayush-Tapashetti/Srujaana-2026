"""F4 and F5 (owner side): generate the agreement, send it, recap in chat."""

from __future__ import annotations

import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.lookup import get_agreement_or_404, get_conversation_or_404
from app.core.config import settings
from app.core.db import get_session
from app.models.agreement import (
    Agreement,
    AgreementStatus,
    ClauseResponse,
    ConfirmationLink,
    ResponseAction,
)
from app.models.analysis import Analysis, ExtractedTerm, Severity, TermStatus
from app.models.base import utcnow
from app.models.conversation import Message
from app.models.evidence import EventType
from app.schemas.agreement import (
    AgreementOut,
    ClauseEditRequest,
    ClauseOut,
    ClauseResponseOut,
    ProposalOut,
    GenerateRequest,
    RecapOut,
    RecapReplyRequest,
    SendResponse,
    Tone,
)
from app.services import clause_builder
from app.services.proposals import is_owner_proposal, pending_proposals
from app.services.evidence_chain import append_event
from app.services.extractor import ResolvedTerm, Revision

router = APIRouter(prefix="/api/agreements", tags=["agreements"])


def _tones(summary_lines: str) -> list[Tone]:
    """Three fixed tones. No LLM (D3): the owner's own voice matters more
    than a generated one, and a static string cannot go off-message."""
    return [
        Tone(
            key="warm",
            label="Warm",
            message=(
                "Hi! Just so we're both on the same page, here's what I "
                "understood we agreed:\n\n"
                f"{summary_lines}\n\n"
                "Does that look right to you? Happy to change anything."
            ),
        ),
        Tone(
            key="neutral",
            label="Neutral",
            message=(
                "Hi, summarising what we agreed so we both have a record:\n\n"
                f"{summary_lines}\n\n"
                "Please confirm, or tell me what to correct."
            ),
        ),
        Tone(
            key="formal",
            label="Formal",
            message=(
                "Dear Sir/Madam,\n\nPlease find below a summary of the terms "
                "discussed:\n\n"
                f"{summary_lines}\n\n"
                "Kindly confirm these terms at your convenience, or advise of "
                "any correction.\n\nRegards"
            ),
        ),
    ]


def _summary_lines(agreement: Agreement) -> str:
    return "\n".join(
        f"- {c['heading']}: {c['body']}"
        for c in agreement.clauses
        if not c.get("is_placeholder")
    )


def _to_resolved(rows: list[ExtractedTerm]) -> list[ResolvedTerm]:
    return [
        ResolvedTerm(
            type=row.type,
            value=row.value or "",
            source_message_ids=row.source_message_ids,
            confidence=row.confidence,
            status=row.status,
            revision_state=row.revision_state,
            revision_history=[
                Revision(
                    value=r["value"], source_message_ids=r["source_message_ids"]
                )
                for r in (row.revision_history or [])
            ],
        )
        for row in rows
    ]


def _responses(session: Session, agreement_id: int) -> list[ClauseResponseOut]:
    rows = session.exec(
        select(ClauseResponse)
        .where(ClauseResponse.agreement_id == agreement_id)
        .order_by(ClauseResponse.id)
    ).all()
    rows = [r for r in rows if not is_owner_proposal(r)]
    return [
        ClauseResponseOut(
            clause_id=r.clause_id,
            action=r.action,
            comment=r.comment,
            typed_name=r.typed_name,
            responded_at=r.responded_at,
        )
        for r in rows
    ]


def to_agreement_out(session: Session, agreement: Agreement) -> AgreementOut:
    pending = pending_proposals(session, agreement.id)
    built_summary = next(
        (c["body"] for c in agreement.clauses if c["id"] == "_summary"), None
    )
    return AgreementOut(
        id=agreement.id,
        conversation_id=agreement.conversation_id,
        version=agreement.version,
        status=agreement.status,
        created_at=agreement.created_at,
        summary=built_summary
        or f"{len([c for c in agreement.clauses if not c['is_placeholder']])} "
        f"of {len(agreement.clauses)} terms were read from the chat.",
        notice=clause_builder.NOT_LEGAL_ADVICE,
        clauses=[
            ClauseOut(
                **c,
                is_pending=c["id"] in pending,
                proposed_value=pending.get(c["id"]),
            )
            for c in agreement.clauses
        ],
        clauses_hash=agreement.clauses_hash,
        override_reason=agreement.override_reason,
        responses=_responses(session, agreement.id),
    )


@router.post(
    "/{conversation_id}/generate",
    response_model=AgreementOut,
    status_code=status.HTTP_201_CREATED,
)
def generate(
    conversation_id: int,
    body: GenerateRequest | None = None,
    session: Session = Depends(get_session),
) -> AgreementOut:
    get_conversation_or_404(session, conversation_id)

    analysis = session.exec(
        select(Analysis)
        .where(Analysis.conversation_id == conversation_id)
        .order_by(Analysis.id.desc())
        .limit(1)
    ).first()
    if analysis is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Analyse the chat before generating an agreement.",
        )

    rows = list(
        session.exec(
            select(ExtractedTerm).where(ExtractedTerm.analysis_id == analysis.id)
        ).all()
    )
    built = clause_builder.build(_to_resolved(rows))

    previous = session.exec(
        select(Agreement)
        .where(Agreement.conversation_id == conversation_id)
        .order_by(Agreement.version.desc())
        .limit(1)
    ).first()

    agreement = Agreement(
        conversation_id=conversation_id,
        analysis_id=analysis.id,
        version=1 if previous is None else previous.version + 1,
        clauses=built.as_dicts(),
        clauses_hash=built.clauses_hash,
        override_reason=(body.override_reason if body else None),
    )
    session.add(agreement)
    session.flush()

    append_event(
        session,
        conversation_id=conversation_id,
        event_type=EventType.AGREEMENT_GENERATED,
        payload={
            "agreement_id": agreement.id,
            "version": agreement.version,
            "clauses_hash": built.clauses_hash,
            "readiness": analysis.readiness.value,
            # D8: an override is never silent; it lives in the chain.
            "override_reason": agreement.override_reason,
        },
    )
    session.commit()
    session.refresh(agreement)

    out = to_agreement_out(session, agreement)
    out.summary = built.summary
    return out


@router.get("/by-conversation/{conversation_id}", response_model=AgreementOut)
def latest_for_conversation(
    conversation_id: int,
    session: Session = Depends(get_session),
) -> AgreementOut:
    """The newest draft for a chat, so the agreement page survives a reload."""
    get_conversation_or_404(session, conversation_id)
    agreement = session.exec(
        select(Agreement)
        .where(Agreement.conversation_id == conversation_id)
        .order_by(Agreement.version.desc())
        .limit(1)
    ).first()
    if agreement is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "No agreement has been drafted for this chat yet."
        )
    return to_agreement_out(session, agreement)


@router.get("/{agreement_id}", response_model=AgreementOut)
def read_agreement(
    agreement_id: int,
    session: Session = Depends(get_session),
) -> AgreementOut:
    agreement = get_agreement_or_404(session, agreement_id)
    return to_agreement_out(session, agreement)


def _guard_red(session: Session, agreement: Agreement) -> None:
    """D8: Red blocks sending unless the owner recorded an override."""
    analysis = session.get(Analysis, agreement.analysis_id)
    if (
        analysis is not None
        and analysis.readiness is Severity.RED
        and not agreement.override_reason
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "A critical term is missing or unconfirmed. Resolve it first, or "
            "regenerate with an override reason, which will be recorded.",
        )


@router.post("/{agreement_id}/send", response_model=SendResponse)
def send_for_confirmation(
    agreement_id: int,
    session: Session = Depends(get_session),
) -> SendResponse:
    """Route A: mint a one-time link and the message to paste with it."""
    agreement = get_agreement_or_404(session, agreement_id)
    _guard_red(session, agreement)

    link = ConfirmationLink(
        agreement_id=agreement.id,
        token=secrets.token_urlsafe(32),
        expires_at=utcnow() + timedelta(hours=settings.confirm_link_ttl_hours),
    )
    session.add(link)

    agreement.status = AgreementStatus.SENT
    session.add(agreement)

    append_event(
        session,
        conversation_id=agreement.conversation_id,
        event_type=EventType.AGREEMENT_SENT,
        payload={
            "agreement_id": agreement.id,
            "route": "A",
            "clauses_hash": agreement.clauses_hash,
            "expires_at": link.expires_at.isoformat(),
        },
    )
    session.commit()

    confirm_url = f"/confirm/{link.token}"
    lines = _summary_lines(agreement)
    tones = _tones(f"{lines}\n\nConfirm here: {confirm_url}")

    return SendResponse(
        agreement_id=agreement.id,
        status=AgreementStatus.SENT,
        tones=tones,
        confirm_url=confirm_url,
        expires_at=link.expires_at,
    )


@router.post("/{agreement_id}/clauses/{clause_id}/propose", response_model=ProposalOut)
def propose_clause_edit(
    agreement_id: int,
    clause_id: str,
    body: ClauseEditRequest,
    session: Session = Depends(get_session),
) -> ProposalOut:
    """Owner drafts a change inside the app, gets a ready-to-paste WhatsApp
    message, and the clause shows as pending.

    The agreement text and hash are deliberately NOT changed: a variation
    binds only once the other side agrees (s.62), and that happens in the
    chat or on the confirmation link, not here.
    """
    agreement = get_agreement_or_404(session, agreement_id)
    clause = next((c for c in agreement.clauses if c["id"] == clause_id), None)
    if clause is None or clause_id.startswith("_"):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That clause was not found.")

    new_body = body.new_body.strip()
    if not new_body:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Type the change you want to propose.")

    session.add(
        ClauseResponse(
            agreement_id=agreement.id,
            link_id=None,
            clause_id=clause_id,
            action=ResponseAction.SUGGEST_CHANGE,
            comment=new_body,
            typed_name="Owner (in the app)",
            clauses_hash_seen=agreement.clauses_hash,
        )
    )
    session.commit()

    snippet = (
        f"Hi, regarding our agreement draft, we need to update "
        f"{clause['heading']} to: \"{new_body}\". Please confirm if this works."
    )
    return ProposalOut(clause_id=clause_id, proposed_value=new_body, whatsapp_snippet=snippet)


@router.get("/{agreement_id}/recap", response_model=RecapOut)
def recap(
    agreement_id: int,
    session: Session = Depends(get_session),
) -> RecapOut:
    """Route B: a message to paste into the same WhatsApp chat.

    No link and no app on the other side, which is the realistic path: the
    owner is talking to a customer they do not want to send paperwork to.
    """
    agreement = get_agreement_or_404(session, agreement_id)
    _guard_red(session, agreement)

    return RecapOut(agreement_id=agreement.id, tones=_tones(_summary_lines(agreement)))


@router.post("/{agreement_id}/recap-reply", response_model=AgreementOut)
def attach_recap_reply(
    agreement_id: int,
    body: RecapReplyRequest,
    session: Session = Depends(get_session),
) -> AgreementOut:
    """Route B part two: the owner re-uploads the chat and marks the reply
    that confirms the recap. That message joins the evidence chain."""
    agreement = get_agreement_or_404(session, agreement_id)

    # The re-uploaded chat must be this account's too.
    get_conversation_or_404(session, body.conversation_id)
    message = session.exec(
        select(Message)
        .where(Message.conversation_id == body.conversation_id)
        .where(Message.index == body.message_index)
    ).first()
    if message is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"No message at position {body.message_index} in that chat.",
        )

    session.add(
        ClauseResponse(
            agreement_id=agreement.id,
            link_id=None,
            clause_id="_all",
            action=ResponseAction.AGREE,
            comment=message.body[:500],
            typed_name=body.typed_name,
            clauses_hash_seen=agreement.clauses_hash,
        )
    )
    agreement.status = AgreementStatus.CONFIRMED
    session.add(agreement)

    append_event(
        session,
        conversation_id=agreement.conversation_id,
        event_type=EventType.RECAP_REPLY,
        payload={
            "agreement_id": agreement.id,
            "route": "B",
            "source_conversation_id": body.conversation_id,
            "source_message_index": body.message_index,
            "message_text": message.body[:500],
            "clauses_hash": agreement.clauses_hash,
            "typed_name": body.typed_name,
        },
    )
    session.commit()
    session.refresh(agreement)
    return to_agreement_out(session, agreement)
