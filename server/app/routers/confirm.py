"""F5 Route A, counterparty side.

No account, no app, no OTP (D3). The other party opens a one-time link,
answers each clause, types their name, and ticks that they have read the
terms. What is recorded is an acknowledgement, and the UI says so on every
screen.

The hash of the clauses they were shown is stored with the response, so a
later edit to the agreement cannot be presented as the thing they agreed to.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.db import get_session
from app.models.agreement import (
    Agreement,
    AgreementStatus,
    ClauseResponse,
    ConfirmationLink,
    ResponseAction,
)
from app.models.base import utcnow
from app.models.evidence import EventType
from app.schemas.agreement import ClauseOut, ConfirmRequest, ConfirmViewOut
from app.services import clause_builder
from app.services.evidence_chain import append_event
from app.services.proposals import pending_proposals

router = APIRouter(prefix="/api/confirm", tags=["confirm"])


def _link(session: Session, token: str) -> ConfirmationLink:
    link = session.exec(
        select(ConfirmationLink).where(ConfirmationLink.token == token)
    ).first()
    if link is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "This confirmation link is not valid. Ask the sender for a new one.",
        )
    return link


def _expired(link: ConfirmationLink) -> bool:
    expires_at = link.expires_at
    if expires_at.tzinfo is None:  # SQLite round-trips can drop the tzinfo
        from datetime import timezone

        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at < utcnow()


def _clauses_out(session: Session, agreement: Agreement) -> list[ClauseOut]:
    """Clauses as the other party sees them, with any pending proposal."""
    pending = pending_proposals(session, agreement.id)
    return [
        ClauseOut(**c, is_pending=c["id"] in pending, proposed_value=pending.get(c["id"]))
        for c in agreement.clauses
    ]


@router.get("/{token}", response_model=ConfirmViewOut)
def view(token: str, session: Session = Depends(get_session)) -> ConfirmViewOut:
    link = _link(session, token)
    agreement = session.get(Agreement, link.agreement_id)
    if agreement is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agreement not found.")

    return ConfirmViewOut(
        agreement_id=agreement.id,
        clauses=_clauses_out(session, agreement),
        clauses_hash=agreement.clauses_hash,
        already_used=link.used_at is not None,
        expired=_expired(link),
    )


@router.post("/{token}", response_model=ConfirmViewOut)
def respond(
    token: str,
    body: ConfirmRequest,
    session: Session = Depends(get_session),
) -> ConfirmViewOut:
    link = _link(session, token)

    if link.used_at is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "This link has already been used. Ask the sender for a new one.",
        )
    if _expired(link):
        raise HTTPException(
            status.HTTP_410_GONE,
            "This link has expired. Ask the sender for a new one.",
        )
    if not body.read_confirmation:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Please tick that you have read the terms before submitting.",
        )

    agreement = session.get(Agreement, link.agreement_id)
    if agreement is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agreement not found.")

    valid_ids = {c["id"] for c in agreement.clauses}
    unknown = [a.clause_id for a in body.answers if a.clause_id not in valid_ids]
    if unknown:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Unknown clause(s): {', '.join(unknown)}.",
        )

    pending = pending_proposals(session, agreement.id)
    for answer in body.answers:
        if answer.proposal and answer.clause_id not in pending:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "There is no proposed change on one of those parts any more. Reload the page.",
            )
        if answer.proposal and answer.action is not ResponseAction.AGREE:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Accepting or declining a proposed change is an 'agree' answer.",
            )

    accepted = {
        a.clause_id: pending[a.clause_id] for a in body.answers if a.proposal == "accept"
    }
    declined = [a.clause_id for a in body.answers if a.proposal == "reject"]

    # An accepted change varies the agreement (s.62), so it becomes a new
    # version with a new fingerprint. The earlier version stays untouched.
    seen_agreement = agreement
    if accepted:
        new_clauses = []
        for c in agreement.clauses:
            c = dict(c)
            if c["id"] in accepted:
                c["body"] = accepted[c["id"]]
                c["status"] = "clear"
                c["is_placeholder"] = False
            new_clauses.append(c)
        latest = session.exec(
            select(Agreement)
            .where(Agreement.conversation_id == agreement.conversation_id)
            .order_by(Agreement.version.desc())
            .limit(1)
        ).first()
        agreement = Agreement(
            conversation_id=agreement.conversation_id,
            analysis_id=agreement.analysis_id,
            version=(latest.version if latest else agreement.version) + 1,
            clauses=new_clauses,
            clauses_hash=clause_builder.hash_clauses(new_clauses),
            override_reason=agreement.override_reason,
        )
        session.add(agreement)
        session.flush()

    for answer in body.answers:
        comment = answer.comment
        if answer.proposal == "accept":
            comment = f"Accepted the proposed change: {accepted[answer.clause_id]}"
        elif answer.proposal == "reject":
            comment = f"Declined the proposed change: {pending[answer.clause_id]}"
        session.add(
            ClauseResponse(
                agreement_id=agreement.id,
                link_id=link.id,
                clause_id=answer.clause_id,
                action=answer.action,
                comment=comment,
                typed_name=body.typed_name.strip(),
                # The text this person actually saw: for an accepted change,
                # that is the new version's wording and fingerprint.
                clauses_hash_seen=agreement.clauses_hash,
            )
        )

    if accepted:
        # Proposals the other side did not answer stay pending on the new version.
        answered = {a.clause_id for a in body.answers}
        for clause_id, text in pending.items():
            if clause_id not in answered:
                session.add(
                    ClauseResponse(
                        agreement_id=agreement.id,
                        link_id=None,
                        clause_id=clause_id,
                        action=ResponseAction.SUGGEST_CHANGE,
                        comment=text,
                        typed_name="owner",
                        clauses_hash_seen=agreement.clauses_hash,
                    )
                )

    # A change request reopens only the affected clause, so the rest of the
    # agreement stays agreed rather than everything resetting to draft.
    changes = [
        a.clause_id
        for a in body.answers
        if a.action is not ResponseAction.AGREE
    ]
    agreement.status = (
        AgreementStatus.CHANGES_REQUESTED if changes else AgreementStatus.CONFIRMED
    )
    session.add(agreement)

    link.used_at = utcnow()
    session.add(link)

    append_event(
        session,
        conversation_id=agreement.conversation_id,
        event_type=EventType.COUNTERPARTY_RESPONSE,
        payload={
            "agreement_id": agreement.id,
            "route": "A",
            "typed_name": body.typed_name.strip(),
            "clauses_hash_seen": agreement.clauses_hash,
            "accepted_proposals": accepted,
            "declined_proposals": declined,
            "previous_agreement_id": seen_agreement.id if accepted else None,
            "previous_clauses_hash": seen_agreement.clauses_hash if accepted else None,
            "answers": [
                {
                    "clause_id": a.clause_id,
                    "action": a.action.value,
                    "comment": a.comment,
                    "proposal": a.proposal,
                }
                for a in body.answers
            ],
            "reopened_clauses": changes,
            "note": "Acknowledgement, not an electronic signature.",
        },
    )
    session.commit()
    session.refresh(agreement)

    return ConfirmViewOut(
        agreement_id=agreement.id,
        clauses=_clauses_out(session, agreement),
        clauses_hash=agreement.clauses_hash,
        already_used=True,
        expired=False,
    )
