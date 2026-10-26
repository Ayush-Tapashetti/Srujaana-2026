from datetime import datetime
from enum import Enum

from sqlmodel import JSON, Column, Field, SQLModel

from app.models.base import TimestampMixin, utcnow


class AgreementStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    CHANGES_REQUESTED = "changes_requested"
    CONFIRMED = "confirmed"


class ResponseAction(str, Enum):
    AGREE = "agree"
    SUGGEST_CHANGE = "suggest_change"
    ASK_QUESTION = "ask_question"


class Agreement(TimestampMixin, table=True):
    __tablename__ = "agreements"

    id: int | None = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="conversations.id", index=True)
    analysis_id: int = Field(foreign_key="analyses.id")

    version: int = Field(default=1)
    status: AgreementStatus = Field(default=AgreementStatus.DRAFT)

    # The clause list exactly as built by clause_builder, stored so the hash
    # stays meaningful even if the analysis is re-run later.
    clauses: list[dict] = Field(default_factory=list, sa_column=Column(JSON))
    clauses_hash: str

    # Set when the owner sends despite a Red flag (D8). Recorded, never silent.
    override_reason: str | None = Field(default=None)


class ConfirmationLink(SQLModel, table=True):
    """Route A. A one-time, expiring token. No OTP and no identity check:
    what this records is an acknowledgement, not an electronic signature."""

    __tablename__ = "confirmation_links"

    id: int | None = Field(default=None, primary_key=True)
    agreement_id: int = Field(foreign_key="agreements.id", index=True)

    token: str = Field(index=True, unique=True)
    created_at: datetime = Field(default_factory=utcnow)
    expires_at: datetime
    used_at: datetime | None = Field(default=None)


class ClauseResponse(SQLModel, table=True):
    """One counterparty answer to one clause."""

    __tablename__ = "clause_responses"

    id: int | None = Field(default=None, primary_key=True)
    agreement_id: int = Field(foreign_key="agreements.id", index=True)
    link_id: int | None = Field(default=None, foreign_key="confirmation_links.id")

    clause_id: str
    action: ResponseAction
    comment: str | None = Field(default=None)

    typed_name: str
    # Hash of the clause values the responder actually saw, so a later edit
    # to the agreement cannot be passed off as the thing they agreed to.
    clauses_hash_seen: str
    responded_at: datetime = Field(default_factory=utcnow)
