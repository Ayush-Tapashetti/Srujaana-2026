"""Response shapes for F1. Mirror these in client/src/types/.

Fix this contract early: Person B is blocked on it, and changing a field
name at hour 30 breaks the frontend silently.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, NaiveDatetime

from app.services.chat_parser import DateOrder, MessageKind


class MessageOut(BaseModel):
    index: int
    # Naive: the export has no timezone. See models/conversation.py.
    timestamp: NaiveDatetime
    sender: str | None
    body: str
    kind: MessageKind


class MaskedDataNote(BaseModel):
    """Shown in the UI as "We hid 2 phone numbers and 1 email before
    analysis" (F1, and the P1-4 preview later)."""

    counts: dict[str, int] = Field(default_factory=dict)
    total: int = 0


class ConversationOut(BaseModel):
    id: int
    original_filename: str
    content_sha256: str
    byte_size: int
    created_at: datetime

    date_order: DateOrder
    participants: list[str]
    warnings: list[str]
    attachment_indices: list[int]

    is_sample: bool
    sample_label: str | None

    message_count: int
    messages: list[MessageOut]
    masked: MaskedDataNote

    # True when this exact file had already been uploaded, so the existing
    # record was returned instead of creating a duplicate.
    deduplicated: bool = False


class ConversationSummary(BaseModel):
    """Row shape for the sample-chat dropdown."""

    id: int
    label: str
    message_count: int
    participants: list[str]
    created_at: datetime | None = None


class PasteRequest(BaseModel):
    text: str = Field(min_length=1)
    filename: str = "pasted-chat.txt"


class ErrorOut(BaseModel):
    detail: str


class MaskedLine(BaseModel):
    """One message: what the chat says, and what the model is shown."""

    index: int
    sender: str | None
    original: str
    sent: str | None  # None: never sent (system line)
    masked: bool  # an identifier in this line was replaced by a token
    withheld: bool  # read as an instruction to an AI, so not sent at all


class MaskedToken(BaseModel):
    token: str  # "<PHONE_1>"
    label: str  # "PHONE"
    occurrences: int


class MaskedPreviewOut(BaseModel):
    """P1-4: the before/after view of D6."""

    conversation_id: int
    prompt_version: str
    counts: dict[str, int]
    total: int
    tokens: list[MaskedToken]
    lines: list[MaskedLine]
    leak_check_passed: bool  # no recognised identifier left in any sent line
