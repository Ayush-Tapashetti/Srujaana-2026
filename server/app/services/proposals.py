"""Owner-proposed clause edits, shared by the owner and counterparty routers.

A proposal is stored as an owner-side SUGGEST_CHANGE row (no confirmation
link) in clause_responses, so no schema change is needed. It stays pending
until the other side answers that clause through a link, which resolves it
either way (accepted or declined).
"""

from __future__ import annotations

from sqlmodel import Session, select

from app.models.agreement import ClauseResponse, ResponseAction


def is_owner_proposal(row: ClauseResponse) -> bool:
    return row.link_id is None and row.action is ResponseAction.SUGGEST_CHANGE


def pending_proposals(session: Session, agreement_id: int) -> dict[str, str]:
    """clause id -> latest proposed text the other side has not answered yet."""
    rows = session.exec(
        select(ClauseResponse)
        .where(ClauseResponse.agreement_id == agreement_id)
        .order_by(ClauseResponse.id)
    ).all()
    pending: dict[str, str] = {}
    for r in rows:
        if is_owner_proposal(r):
            if r.comment:
                pending[r.clause_id] = r.comment
        elif r.link_id is not None:
            # The other side answered this clause: the proposal is settled.
            pending.pop(r.clause_id, None)
    return pending
