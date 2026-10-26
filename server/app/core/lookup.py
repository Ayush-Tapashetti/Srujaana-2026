"""Look up a chat or an agreement by id, or 404.

The app has no accounts: every chat is visible to whoever can reach the
server. The one thing that is still permission-by-secret is a link token
(/api/confirm/{token} and /api/pack/{token}), which is handled in those
routers. Run this on a private machine or behind your own access control.
"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlmodel import Session

from app.models.agreement import Agreement
from app.models.conversation import Conversation


def get_conversation_or_404(session: Session, conversation_id: int) -> Conversation:
    conversation = session.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found.")
    return conversation


def get_agreement_or_404(session: Session, agreement_id: int) -> Agreement:
    agreement = session.get(Agreement, agreement_id)
    if agreement is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agreement not found.")
    return agreement
