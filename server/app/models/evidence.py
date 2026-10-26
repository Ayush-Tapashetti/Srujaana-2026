from datetime import datetime
from enum import Enum

from sqlmodel import JSON, Column, Field, SQLModel

from app.models.base import utcnow


class EventType(str, Enum):
    UPLOAD = "upload"
    EXTRACTION = "extraction"
    AGREEMENT_GENERATED = "agreement_generated"
    AGREEMENT_SENT = "agreement_sent"
    COUNTERPARTY_RESPONSE = "counterparty_response"
    RECAP_REPLY = "recap_reply"
    OVERRIDE_ACKNOWLEDGED = "override_acknowledged"


class EvidenceEvent(SQLModel, table=True):
    """Append-only. There is deliberately no update or delete path for these
    rows: the integrity claim is only credible if the schema itself forbids
    mutation. The one exception is the DEMO_TAMPER_ENABLED endpoint, which
    exists solely to break the chain on stage."""

    __tablename__ = "evidence_events"

    id: int | None = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="conversations.id", index=True)

    sequence: int = Field(index=True)  # 0-based, contiguous per conversation
    type: EventType
    occurred_at: datetime = Field(default_factory=utcnow)

    payload: dict = Field(default_factory=dict, sa_column=Column(JSON))
    payload_sha256: str
    prev_hash: str
    chain_hash: str
