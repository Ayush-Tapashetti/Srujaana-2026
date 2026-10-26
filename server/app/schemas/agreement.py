"""F4 and F5 shapes. Mirror in client/src/types/agreement.ts."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.agreement import AgreementStatus, ResponseAction

ACKNOWLEDGEMENT_NOTICE = (
    "Acknowledgement recorded. This is not a legal electronic signature."
)


class ClauseOut(BaseModel):
    id: str
    heading: str
    body: str
    status: str
    source_message_ids: list[int]
    is_placeholder: bool
    # An in-app proposed edit that the other side has not yet confirmed in the
    # chat (Contract Act s.62). Never changes the clause text or the hash.
    is_pending: bool = False
    proposed_value: str | None = None


class AgreementOut(BaseModel):
    id: int
    conversation_id: int
    version: int
    status: AgreementStatus
    created_at: datetime

    summary: str
    notice: str
    clauses: list[ClauseOut]
    clauses_hash: str

    override_reason: str | None = None
    responses: list["ClauseResponseOut"] = Field(default_factory=list)


class ClauseEditRequest(BaseModel):
    new_body: str = Field(min_length=1, max_length=1000)
    # The clause id is already in the URL; accepted here only for clients
    # that send it, and ignored.
    clause_id: str | None = None


class ProposalOut(BaseModel):
    status: str = "pending_confirmation"
    clause_id: str
    proposed_value: str
    whatsapp_snippet: str
    notice: str = (
        "Pending until the other side agrees in the chat. "
        "The agreement text and its fingerprint are unchanged."
    )


class GenerateRequest(BaseModel):
    # D8: Red blocks sending. The owner may still proceed, but only with a
    # reason that is recorded in the evidence chain, never silently.
    override_reason: str | None = None


class Tone(BaseModel):
    key: str
    label: str
    message: str


class SendResponse(BaseModel):
    agreement_id: int
    status: AgreementStatus
    tones: list[Tone]
    confirm_url: str
    expires_at: datetime
    notice: str = ACKNOWLEDGEMENT_NOTICE


class ConfirmViewOut(BaseModel):
    """What the counterparty sees. Read-only, no app, no account."""

    agreement_id: int
    clauses: list[ClauseOut]
    clauses_hash: str
    already_used: bool
    expired: bool
    notice: str = ACKNOWLEDGEMENT_NOTICE


class ClauseAnswer(BaseModel):
    clause_id: str
    action: ResponseAction
    comment: str | None = None
    # Set only when answering the owner's pending proposal for this clause:
    # "accept" makes the proposed wording part of the agreement, "reject"
    # keeps the current wording.
    proposal: Literal["accept", "reject"] | None = None


class ConfirmRequest(BaseModel):
    typed_name: str = Field(min_length=2, max_length=120)
    read_confirmation: bool
    answers: list[ClauseAnswer] = Field(min_length=1)


class ClauseResponseOut(BaseModel):
    clause_id: str
    action: ResponseAction
    comment: str | None
    typed_name: str
    responded_at: datetime


class RecapOut(BaseModel):
    """Route B: text the owner pastes back into the same WhatsApp chat.

    No link, no app on the other side. The owner later re-uploads the
    export and marks the reply that confirms it.
    """

    agreement_id: int
    tones: list[Tone]
    notice: str = ACKNOWLEDGEMENT_NOTICE


class RecapReplyRequest(BaseModel):
    conversation_id: int
    message_index: int
    typed_name: str = Field(min_length=2, max_length=120)


AgreementOut.model_rebuild()
