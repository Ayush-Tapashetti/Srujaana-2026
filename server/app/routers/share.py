"""Share with a CA or lawyer: a read-only evidence summary behind a link.

Two halves, kept apart:

  owner side   no sign-in         create, list and revoke links
  public side  token is the key   GET /api/pack/{token}

The public side builds the pack from functions the app already has: the
analysis, the agreement, verify_chain and the certificate draft. Nothing is
copied or stored, so the pack can never show something the owner's own pages
do not.

Privacy, decided here rather than left to the page:

  * Identifiers (phone, PAN, Aadhaar, GSTIN, email, UPI) are masked in every
    sentence that comes from the chat, with the same masker the AI step uses.
  * Raw evidence payloads are NOT returned. They can carry file names and
    free text from the chat. The pack gets one masked sentence per event
    plus the hashes, which are all a verifier needs.
  * Hashes are never masked. A hex digest can contain a long run of digits
    that an identifier pattern would "mask", corrupting what is being checked.
  * The link expires (default 7 days), can be revoked, and the response is
    marked noindex and no-store.

Wording: this is an evidence summary for review. It is not a court-ready or
legal pack, Part A stays a draft the party completes, and Part B needs an
expert.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.core.lookup import get_conversation_or_404
from app.core.db import get_session
from app.models.agreement import Agreement
from app.models.analysis import Severity
from app.models.base import utcnow
from app.models.conversation import Conversation, Message
from app.models.evidence import EventType, EvidenceEvent
from app.models.share import ShareLink
from app.routers.agreements import to_agreement_out
from app.routers.analysis import _latest_analysis, _to_out
from app.routers.evidence import LIMIT_NOTE, certificate_draft
from app.services import extractor, pii_masker
from app.services.evidence_chain import ALGORITHM, verify_chain

owner_router = APIRouter(prefix="/api/evidence", tags=["share"])
public_router = APIRouter(prefix="/api/pack", tags=["share"])

DEFAULT_DAYS = 7
MAX_DAYS = 30
MAX_ACTIVE_LINKS = 10

PACK_TITLE = "Evidence summary for review"
PACK_NOTICES = [
    "This is an evidence summary for review. It is not a legal opinion and it is not a court-ready bundle.",
    "The certificate below is a draft of Part A. The party completes it, ticks only what they can confirm, and signs. "
    "Part B must be completed by an expert, and this app does not produce it.",
    "Phone numbers, PAN, Aadhaar, GSTIN, email addresses and UPI IDs from the chat are hidden in this view.",
    LIMIT_NOTE,
]


# --------------------------------------------------------------------------
# Shapes
# --------------------------------------------------------------------------


class ShareCreate(BaseModel):
    days: int = Field(DEFAULT_DAYS, ge=1, le=MAX_DAYS)


class ShareOut(BaseModel):
    id: int
    url: str  # path only; the page adds its own origin
    created_at: datetime
    expires_at: datetime
    revoked: bool
    expired: bool
    view_count: int
    last_viewed_at: datetime | None = None


class PackCase(BaseModel):
    file_name: str
    participants: list[str]
    message_count: int
    period: str


class PackTerm(BaseModel):
    type: str
    value: str | None
    status: str
    revision_state: str
    source_message_ids: list[int]


class PackFlag(BaseModel):
    severity: str
    title: str
    why_it_matters: str
    statute: str
    section: str
    suggested_question: str | None
    source_message_ids: list[int]


class PackSummary(BaseModel):
    readiness: str
    terms: list[PackTerm]
    flags: list[PackFlag]


class PackSource(BaseModel):
    """One chat message cited by a term, flag or clause, identifiers masked."""

    index: int
    sender: str | None
    timestamp: datetime
    body: str


class PackClause(BaseModel):
    id: str
    heading: str
    body: str
    status: str
    source_message_ids: list[int]
    is_placeholder: bool


class PackResponse(BaseModel):
    clause_id: str
    action: str
    comment: str | None
    typed_name: str
    responded_at: datetime


class PackAgreement(BaseModel):
    version: int
    status: str
    clauses_hash: str
    clauses: list[PackClause]
    responses: list[PackResponse]
    acknowledgement_note: str = "Acknowledgements are recorded answers, not electronic signatures."


class PackEvent(BaseModel):
    sequence: int
    type: EventType
    occurred_at: datetime
    summary: str
    payload_sha256: str
    prev_hash: str
    chain_hash: str
    verified: bool  # False from the first broken event onward


class PackChain(BaseModel):
    algorithm: str
    intact: bool
    checked: int
    broken_at_sequence: int | None
    reason: str | None


class PackField(BaseModel):
    label: str
    value: str
    source: str


class PackStatement(BaseModel):
    text: str
    affirmed: bool = False  # always False: only the party can affirm


class PackCertificate(BaseModel):
    title: str
    status: str
    record: list[PackField]
    integrity: list[PackField]
    party_fields: list[str]  # left blank on purpose
    statements: list[PackStatement]
    cautions: list[str]


class PackOut(BaseModel):
    title: str = PACK_TITLE
    notices: list[str]
    generated_at: datetime
    expires_at: datetime
    case: PackCase
    summary: PackSummary | None
    sources: list[PackSource]
    agreement: PackAgreement | None
    timeline: list[PackEvent]
    chain: PackChain
    certificate: PackCertificate
    identifiers_hidden: int


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _aware(moment: datetime) -> datetime:
    """SQLite round-trips can drop the tzinfo; every stored time is UTC."""
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=timezone.utc)


def _is_expired(link: ShareLink) -> bool:
    return _aware(link.expires_at) < utcnow()


def _share_out(link: ShareLink) -> ShareOut:
    return ShareOut(
        id=link.id,
        url=f"/pack/{link.token}",
        created_at=link.created_at,
        expires_at=link.expires_at,
        revoked=link.revoked,
        expired=_is_expired(link),
        view_count=link.view_count,
        last_viewed_at=link.last_viewed_at,
    )


def _own_link(session: Session, conversation_id: int, share_id: int) -> ShareLink:
    link = session.get(ShareLink, share_id)
    if link is None or link.conversation_id != conversation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Share link not found.")
    return link


# --------------------------------------------------------------------------
# Owner side
# --------------------------------------------------------------------------


@owner_router.post(
    "/{conversation_id}/share",
    response_model=ShareOut,
    status_code=status.HTTP_201_CREATED,
)
def create_share(
    conversation_id: int,
    body: ShareCreate | None = None,
    session: Session = Depends(get_session),
) -> ShareOut:
    get_conversation_or_404(session, conversation_id)
    days = body.days if body else DEFAULT_DAYS

    now = utcnow()
    active = [
        link
        for link in session.exec(
            select(ShareLink)
            .where(ShareLink.conversation_id == conversation_id)
            .where(ShareLink.revoked == False)  # noqa: E712  (SQL comparison)
        ).all()
        if _aware(link.expires_at) >= now
    ]
    if len(active) >= MAX_ACTIVE_LINKS:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"This chat already has {MAX_ACTIVE_LINKS} active share links. Turn one off first.",
        )

    link = ShareLink(
        conversation_id=conversation_id,
        token=secrets.token_urlsafe(32),
        expires_at=now + timedelta(days=days),
    )
    session.add(link)
    session.commit()
    session.refresh(link)
    return _share_out(link)


@owner_router.get("/{conversation_id}/shares", response_model=list[ShareOut])
def list_shares(
    conversation_id: int,
    session: Session = Depends(get_session),
) -> list[ShareOut]:
    get_conversation_or_404(session, conversation_id)
    links = session.exec(
        select(ShareLink)
        .where(ShareLink.conversation_id == conversation_id)
        .order_by(ShareLink.id.desc())
    ).all()
    return [_share_out(link) for link in links]


@owner_router.post("/{conversation_id}/share/{share_id}/revoke", response_model=ShareOut)
def revoke_share(
    conversation_id: int,
    share_id: int,
    session: Session = Depends(get_session),
) -> ShareOut:
    get_conversation_or_404(session, conversation_id)
    link = _own_link(session, conversation_id, share_id)
    if not link.revoked:
        link.revoked = True
        link.revoked_at = utcnow()
        session.add(link)
        session.commit()
        session.refresh(link)
    return _share_out(link)


# --------------------------------------------------------------------------
# Public side
# --------------------------------------------------------------------------


def _describe(event: EvidenceEvent, hide) -> str:  # noqa: ANN001
    """One masked sentence per event. Never the raw payload."""
    p = event.payload or {}

    def get(key: str, default: str = "") -> str:
        value = p.get(key)
        return default if value is None else str(value)

    kind = event.type
    if kind is EventType.UPLOAD:
        return hide(
            f"Chat file uploaded: {get('filename', 'unnamed file')}, "
            f"{get('message_count', '?')} messages, fingerprinted with {get('algorithm', ALGORITHM)}."
        )
    if kind is EventType.EXTRACTION:
        return f"Terms read from the chat: {get('term_count', '?')} found, readiness {get('readiness', 'unknown')}."
    if kind is EventType.AGREEMENT_GENERATED:
        text = f"Agreement version {get('version', '?')} drafted while readiness was {get('readiness', 'unknown')}."
        if p.get("override_reason"):
            text += f" The owner recorded a reason for proceeding: {get('override_reason')}"
        return hide(text)
    if kind is EventType.AGREEMENT_SENT:
        return "Agreement sent to the other party for confirmation, by a one-time link."
    if kind is EventType.COUNTERPARTY_RESPONSE:
        answers = p.get("answers")
        count = len(answers) if isinstance(answers, list) else 0
        return hide(
            f"{get('typed_name', 'The other party')} answered {count} clause(s). "
            "An acknowledgement, not a signature."
        )
    if kind is EventType.RECAP_REPLY:
        return hide(f"{get('typed_name', 'The other party')} replied in WhatsApp: “{get('message_text')}”")
    if kind is EventType.OVERRIDE_ACKNOWLEDGED:
        return "The owner acknowledged a warning and chose to continue."
    return "Recorded event."


def _link_for_token(session: Session, token: str) -> ShareLink:
    link = session.exec(select(ShareLink).where(ShareLink.token == token)).first()
    if link is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "This link is not valid. Ask the person who sent it for a new one.",
        )
    if link.revoked:
        raise HTTPException(
            status.HTTP_410_GONE,
            "The owner has turned this link off. Ask them for a new one.",
        )
    if _is_expired(link):
        raise HTTPException(
            status.HTTP_410_GONE,
            "This link has expired. Ask the owner for a new one.",
        )
    return link


@public_router.get("/{token}", response_model=PackOut)
def read_pack(
    token: str,
    response: Response,
    session: Session = Depends(get_session),
) -> PackOut:
    # Set first so even error responses are not indexed or cached.
    response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"

    link = _link_for_token(session, token)
    conversation = session.get(Conversation, link.conversation_id)
    if conversation is None:
        raise HTTPException(
            status.HTTP_410_GONE, "This record is no longer available. Ask the owner for a new link."
        )

    messages = list(
        session.exec(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.index)
        ).all()
    )
    # An empty chat cannot be uploaded, but never let the masker be the thing that fails.
    mask = extractor.conversation_mask(messages) if messages else pii_masker.pseudonymise("")

    def hide(text: str | None) -> str:
        return "" if text is None else pii_masker.mask_with(mask, text)

    # ---- chain, verified now ------------------------------------------------
    events = list(
        session.exec(
            select(EvidenceEvent)
            .where(EvidenceEvent.conversation_id == conversation.id)
            .order_by(EvidenceEvent.sequence)
        ).all()
    )
    result = verify_chain(events)
    broken_at = result.broken_at_sequence
    timeline = [
        PackEvent(
            sequence=e.sequence,
            type=e.type,
            occurred_at=e.occurred_at,
            summary=_describe(e, hide),
            payload_sha256=e.payload_sha256,
            prev_hash=e.prev_hash,
            chain_hash=e.chain_hash,
            verified=result.intact or (broken_at is not None and e.sequence < broken_at),
        )
        for e in events
    ]

    # ---- summary: terms and flags ------------------------------------------
    cited: set[int] = set()
    summary: PackSummary | None = None
    analysis = _latest_analysis(session, conversation.id)
    if analysis is not None:
        a = _to_out(session, analysis)
        summary = PackSummary(
            readiness=a.readiness.value,
            terms=[
                PackTerm(
                    type=t.type.value,
                    value=hide(t.value) if t.value is not None else None,
                    status=t.status.value,
                    revision_state=t.revision_state.value,
                    source_message_ids=t.source_message_ids,
                )
                for t in a.terms
            ],
            flags=[
                PackFlag(
                    severity=f.severity.value,
                    title=hide(f.title),
                    why_it_matters=hide(f.why_it_matters),
                    statute=f.statute,
                    section=f.section,
                    suggested_question=hide(f.suggested_question) if f.suggested_question else None,
                    source_message_ids=f.source_message_ids,
                )
                for f in a.flags
                if f.severity is not Severity.GREEN
            ],
        )
        for t in summary.terms:
            cited.update(t.source_message_ids)
        for f in summary.flags:
            cited.update(f.source_message_ids)

    # ---- agreement and who acknowledged it --------------------------------
    agreement_row = session.exec(
        select(Agreement)
        .where(Agreement.conversation_id == conversation.id)
        .order_by(Agreement.version.desc())
        .limit(1)
    ).first()
    agreement: PackAgreement | None = None
    if agreement_row is not None:
        full = to_agreement_out(session, agreement_row)
        agreement = PackAgreement(
            version=full.version,
            status=full.status.value,
            clauses_hash=full.clauses_hash,
            clauses=[
                PackClause(
                    id=c.id,
                    heading=c.heading,
                    body=hide(c.body),
                    status=c.status,
                    source_message_ids=c.source_message_ids,
                    is_placeholder=c.is_placeholder,
                )
                for c in full.clauses
            ],
            responses=[
                PackResponse(
                    clause_id=r.clause_id,
                    action=r.action.value,
                    comment=hide(r.comment) if r.comment else None,
                    typed_name=hide(r.typed_name),
                    responded_at=r.responded_at,
                )
                for r in full.responses
            ],
        )
        for c in agreement.clauses:
            cited.update(c.source_message_ids)

    # ---- the messages those cite, masked ------------------------------------
    sources = [
        PackSource(
            index=m.index,
            sender=hide(m.sender) if m.sender else None,
            timestamp=m.timestamp,
            body=hide(m.body),
        )
        for m in messages
        if m.index in cited
    ]

    # ---- certificate draft: the existing function, as the owner would see it
    draft = certificate_draft(conversation.id, session=session)
    certificate = PackCertificate(
        title=draft.title,
        status=draft.status,
        # Mask what came from the chat (file name, participants). The
        # integrity block is left exactly as computed: hashes must not change.
        record=[PackField(label=f.label, value=hide(f.value), source=f.source) for f in draft.record],
        integrity=[PackField(label=f.label, value=f.value, source=f.source) for f in draft.integrity],
        party_fields=draft.party_fields,
        statements=[PackStatement(text=s.text, affirmed=False) for s in draft.statements],
        cautions=draft.cautions,
    )

    # ---- case header --------------------------------------------------------
    def fmt(dt: datetime) -> str:
        return dt.strftime("%d %b %Y, %H:%M")

    case = PackCase(
        file_name=hide(conversation.original_filename),
        participants=[hide(p) for p in conversation.participants],
        message_count=len(messages),
        period=(f"{fmt(messages[0].timestamp)} to {fmt(messages[-1].timestamp)} (as shown in the export)" if messages else "No messages"),
    )

    # Count this view. A failure here must never stop the pack loading.
    try:
        link.view_count += 1
        link.last_viewed_at = utcnow()
        session.add(link)
        session.commit()
    except Exception:  # noqa: BLE001
        session.rollback()

    return PackOut(
        notices=PACK_NOTICES,
        generated_at=utcnow(),
        expires_at=link.expires_at,
        case=case,
        summary=summary,
        sources=sources,
        agreement=agreement,
        timeline=timeline,
        chain=PackChain(
            algorithm=ALGORITHM,
            intact=result.intact,
            checked=result.checked,
            broken_at_sequence=result.broken_at_sequence,
            reason=result.reason,
        ),
        certificate=certificate,
        identifiers_hidden=sum(mask.masked_counts.values()),
    )
