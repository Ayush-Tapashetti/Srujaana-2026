"""F6 endpoints. Read and verify only: there is no update or delete path.

The tamper endpoint is the single exception and exists purely for the live
demo. It is guarded by DEMO_TAMPER_ENABLED and returns 404 when that flag
is off, so it cannot be reached in a deployed build.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.lookup import get_conversation_or_404
from app.core.config import settings
from app.core.db import get_session
from app.models.conversation import Conversation, Message
from app.models.evidence import EventType, EvidenceEvent
from app.services.evidence_chain import ALGORITHM, _canonical_time, verify_chain

router = APIRouter(prefix="/api/evidence", tags=["evidence"])

LIMIT_NOTE = (
    "This proves nothing has changed since the file was uploaded. It cannot "
    "prove the chat was genuine before upload."
)


class EvidenceEventOut(BaseModel):
    sequence: int
    type: EventType
    occurred_at: datetime
    payload: dict
    payload_sha256: str
    prev_hash: str
    chain_hash: str


class EvidenceChainOut(BaseModel):
    conversation_id: int
    algorithm: str
    events: list[EvidenceEventOut]
    limitation: str = LIMIT_NOTE


class VerificationOut(BaseModel):
    intact: bool
    checked: int
    broken_at_sequence: int | None = None
    reason: str | None = None
    limitation: str = LIMIT_NOTE


def _events(session: Session, conversation_id: int) -> list[EvidenceEvent]:
    get_conversation_or_404(session, conversation_id)
    return list(
        session.exec(
            select(EvidenceEvent)
            .where(EvidenceEvent.conversation_id == conversation_id)
            .order_by(EvidenceEvent.sequence)
        ).all()
    )


@router.get("/{conversation_id}", response_model=EvidenceChainOut)
def read_chain(
    conversation_id: int,
    session: Session = Depends(get_session),
) -> EvidenceChainOut:
    events = _events(session, conversation_id)
    return EvidenceChainOut(
        conversation_id=conversation_id,
        algorithm=ALGORITHM,
        events=[EvidenceEventOut.model_validate(e, from_attributes=True) for e in events],
    )


@router.get("/{conversation_id}/verify", response_model=VerificationOut)
def verify(
    conversation_id: int,
    session: Session = Depends(get_session),
) -> VerificationOut:
    result = verify_chain(_events(session, conversation_id))
    return VerificationOut(
        intact=result.intact,
        checked=result.checked,
        broken_at_sequence=result.broken_at_sequence,
        reason=result.reason,
    )


class CertificateField(BaseModel):
    label: str
    value: str
    source: str  # where the value came from, so the party can check it


class CertificateStatement(BaseModel):
    text: str
    # Always False from the server. Only the party can affirm these; the
    # page renders them as unticked boxes.
    affirmed: bool = False


class CertificateDraftOut(BaseModel):
    """P1-1: BSA 2023 s.63(4) certificate, Part A pre-fill. Nothing stored."""

    conversation_id: int
    title: str
    status: str
    record: list[CertificateField]
    integrity: list[CertificateField]
    party_fields: list[str]  # filled in on the page, never sent back
    statements: list[CertificateStatement]
    chain_intact: bool
    cautions: list[str]
    generated_at: datetime


@router.get("/{conversation_id}/certificate-draft", response_model=CertificateDraftOut)
def certificate_draft(
    conversation_id: int,
    session: Session = Depends(get_session),
) -> CertificateDraftOut:
    """Pre-fills the facts this app knows. The party supplies who they are,
    which device they used, and affirms the statements themselves."""
    events = _events(session, conversation_id)  # 404s for unknown ids
    conversation = session.get(Conversation, conversation_id)
    assert conversation is not None
    messages = list(
        session.exec(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.index)
        ).all()
    )
    result = verify_chain(events)
    genesis = events[0] if events else None
    head = events[-1] if events else None

    def fmt(dt: datetime) -> str:
        return dt.strftime("%d %b %Y, %H:%M")

    span = (
        f"{fmt(messages[0].timestamp)} to {fmt(messages[-1].timestamp)} (as shown in the export)"
        if messages
        else "No messages"
    )

    return CertificateDraftOut(
        conversation_id=conversation_id,
        title="Certificate under section 63(4)(c), Bharatiya Sakshya Adhiniyam, 2023: Part A (draft)",
        status="Draft for the party to review. Not filed, not signed, not legal advice.",
        record=[
            CertificateField(label="Electronic record", value="WhatsApp chat export (text, without media)", source="file type checked at upload"),
            CertificateField(label="File name", value=conversation.original_filename, source="upload"),
            CertificateField(label="File size", value=f"{conversation.byte_size:,} bytes", source="upload"),
            CertificateField(label="Messages", value=str(len(messages)), source="parsed export"),
            CertificateField(label="Participants", value=", ".join(conversation.participants) or "Not identified", source="parsed export"),
            CertificateField(label="Period covered", value=span, source="parsed export"),
            CertificateField(label="How it was produced", value="WhatsApp > chat > More > Export chat > Without media", source="the method this app accepts; confirm it is what you did"),
            CertificateField(label="Received by this app", value=_canonical_time(genesis.occurred_at).replace("+00:00", " UTC") if genesis else "Unknown", source=f"evidence event {genesis.sequence}" if genesis else "none"),
        ],
        integrity=[
            CertificateField(label="Hash algorithm", value=ALGORITHM, source="evidence chain"),
            CertificateField(label="Hash of the file as uploaded", value=conversation.content_sha256, source="computed on the uploaded bytes"),
            CertificateField(label="Evidence chain head", value=head.chain_hash if head else "None", source=f"event {head.sequence}" if head else "none"),
            CertificateField(label="Events in chain", value=str(len(events)), source="evidence chain"),
            CertificateField(
                label="Chain check",
                value="Intact" if result.intact else f"Broken at event {result.broken_at_sequence}",
                source="verified when this draft was generated",
            ),
        ],
        party_fields=[
            "Full name of the person giving this certificate",
            "Position or relationship to the business",
            "Device the chat was exported from (make and model)",
            "Whose phone it is, and who controlled it at the time",
            "Place and date",
        ],
        statements=[
            CertificateStatement(text="The device was regularly used to send and receive messages for this business during the period covered."),
            CertificateStatement(text="Throughout that period the device was operating properly, or any fault did not affect the accuracy of these messages."),
            CertificateStatement(text="The exported file was produced from that device in the ordinary course, and I have not edited it."),
            CertificateStatement(text="The hash value above is the value of the file I uploaded."),
        ],
        chain_intact=result.intact,
        cautions=[
            "Check this wording against the Schedule to the Bharatiya Sakshya Adhiniyam, 2023 before relying on it. This draft follows its structure but is not the official form.",
            "Part A is completed by the party. Part B is completed by an expert, and this app does not produce it.",
            "Only tick a statement you can personally confirm.",
            LIMIT_NOTE,
        ],
        generated_at=datetime.now(timezone.utc),
    )


@router.post("/{conversation_id}/_tamper", response_model=VerificationOut)
def tamper_for_demo(
    conversation_id: int,
    sequence: int = 1,
    session: Session = Depends(get_session),
) -> VerificationOut:
    """Dev-only. Corrupts one stored payload so Verify fails on stage.

    Editing a row by hand in front of a judge with a timer running is how
    demos die. One click, guaranteed red.
    """
    if not settings.demo_tamper_enabled:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found.")
    get_conversation_or_404(session, conversation_id)

    event = session.exec(
        select(EvidenceEvent)
        .where(EvidenceEvent.conversation_id == conversation_id)
        .where(EvidenceEvent.sequence == sequence)
    ).first()
    if event is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"No event at sequence {sequence}."
        )

    altered = dict(event.payload)
    altered["_demo_tampered"] = True
    event.payload = altered  # payload_sha256 deliberately left stale
    session.add(event)
    session.commit()

    result = verify_chain(_events(session, conversation_id))
    return VerificationOut(
        intact=result.intact,
        checked=result.checked,
        broken_at_sequence=result.broken_at_sequence,
        reason=result.reason,
    )
