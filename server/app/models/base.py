from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    """Always timezone-aware. Mixing naive and aware datetimes breaks the
    hash chain, because the two serialise differently."""
    return datetime.now(timezone.utc)


class TimestampMixin(SQLModel):
    created_at: datetime = Field(default_factory=utcnow, nullable=False)
