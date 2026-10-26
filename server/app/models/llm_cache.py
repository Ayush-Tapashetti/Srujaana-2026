from sqlmodel import Field, SQLModel

from app.models.base import TimestampMixin


class LlmCacheEntry(TimestampMixin, table=True):
    """One cached model response (D13).

    Keyed by hash(system + prompt + prompt_version + model), so changing the
    prompt invalidates the cache automatically rather than silently serving
    answers produced by an older instruction.

    Two reasons this exists, both scored: the free tier's tokens-per-minute
    cap is low enough that debugging exhausts it, and a cached run means the
    demo survives a dead network. The UI labels cached results as cached.
    """

    __tablename__ = "llm_cache"

    id: int | None = Field(default=None, primary_key=True)
    cache_key: str = Field(index=True, unique=True)
    model: str
    prompt_version: str
    response_text: str
