from pydantic import NaiveDatetime
from sqlmodel import JSON, Column, Field, Relationship, SQLModel

from app.models.base import TimestampMixin
from app.services.chat_parser import DateOrder, MessageKind


class Conversation(TimestampMixin, table=True):
    __tablename__ = "conversations"

    id: int | None = Field(default=None, primary_key=True)
    original_filename: str
    byte_size: int

    # Unique, so re-uploading the same chat returns the existing analysis
    # instead of spending another LLM call. Also the F6 fingerprint at upload.
    content_sha256: str = Field(index=True, unique=True)

    date_order: DateOrder = Field(default=DateOrder.AMBIGUOUS)
    participants: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    warnings: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    attachment_indices: list[int] = Field(
        default_factory=list, sa_column=Column(JSON)
    )

    # Pre-loaded demo chats, served by GET /api/samples so a judge's
    # "try another input" takes six seconds.
    is_sample: bool = Field(default=False, index=True)
    sample_label: str | None = Field(default=None)

    messages: list["Message"] = Relationship(
        back_populates="conversation",
        sa_relationship_kwargs={"order_by": "Message.index"},
    )


class Message(SQLModel, table=True):
    __tablename__ = "messages"

    id: int | None = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="conversations.id", index=True)

    # 0-based position in the conversation. Everything in this codebase that
    # says `source_message_ids` means a list of THESE, not database ids.
    index: int
    # Naive on purpose. A WhatsApp export records local wall-clock time with
    # no offset, so attaching UTC would invent information we do not have.
    # Only the ORDER of messages matters to the revision logic.
    timestamp: NaiveDatetime
    sender: str | None = Field(default=None)
    body: str
    kind: MessageKind = Field(default=MessageKind.TEXT)

    conversation: Conversation | None = Relationship(back_populates="messages")
