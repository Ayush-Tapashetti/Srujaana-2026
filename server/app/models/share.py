from datetime import datetime

from sqlmodel import Field, SQLModel

from app.models.base import utcnow


class ShareLink(SQLModel, table=True):
    """A read-only link to the evidence summary for one chat, for a CA or lawyer.

    A new table on purpose: create_all adds it to an existing database
    without a reset, and sharing is NOT recorded as an evidence event, which
    would have changed the event types and the hash chain.

    The token is the permission. It is random, expires (default 7 days) and
    can be revoked. Nothing about the chat is stored here.
    """

    __tablename__ = "share_links"

    id: int | None = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="conversations.id", index=True)
    token: str = Field(index=True, unique=True)
    created_at: datetime = Field(default_factory=utcnow)
    expires_at: datetime

    revoked: bool = Field(default=False)
    revoked_at: datetime | None = Field(default=None)

    view_count: int = Field(default=0)
    last_viewed_at: datetime | None = Field(default=None)
