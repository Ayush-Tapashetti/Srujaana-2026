from decimal import Decimal
from enum import Enum

from sqlmodel import JSON, Column, Field, SQLModel

from app.models.base import TimestampMixin


class TermType(str, Enum):
    PARTY = "party"
    SCOPE = "scope"
    QUANTITY = "quantity"
    PRICE = "price"
    ADVANCE = "advance"
    PAYMENT_DUE = "payment_due"
    DELIVERY_DATE = "delivery_date"
    ACCEPTANCE = "acceptance"
    CANCELLATION = "cancellation"
    DISPUTE = "dispute"


#: F3: only these block sending when missing (D7, D8).
CRITICAL_TERMS: frozenset[TermType] = frozenset(
    {
        TermType.PARTY,
        TermType.SCOPE,
        TermType.PRICE,
        TermType.PAYMENT_DUE,
        TermType.DELIVERY_DATE,
    }
)


class TermStatus(str, Enum):
    CLEAR = "clear"
    VAGUE = "vague"  # present but imprecise -> Yellow (LLM decides)
    MISSING = "missing"  # absent -> Red for critical terms (code decides)
    CONFLICTED = "conflicted"  # revised, never settled -> Red (code decides)


class Severity(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class RevisionState(str, Enum):
    """Whether a later value actually replaced the earlier one.

    Contract Act s.62: varying a contract needs BOTH parties. A later message
    proposing a new price that the other side never answered is a proposal to
    vary, not a variation. Deciding this in code (did the counterparty send
    anything after the revision?) is what separates test T4 from T5 and keeps
    the judgment out of the LLM's hands.
    """

    NONE = "none"  # never revised
    SETTLED = "settled"  # revised, and the other party replied afterwards
    UNRESOLVED = "unresolved"  # revised, no response -> CONFLICTED


class Analysis(TimestampMixin, table=True):
    __tablename__ = "analyses"

    id: int | None = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="conversations.id", index=True)

    model_used: str
    prompt_version: str
    from_cache: bool = Field(default=False)
    readiness: Severity = Field(default=Severity.RED)


class ExtractedTerm(SQLModel, table=True):
    __tablename__ = "extracted_terms"

    id: int | None = Field(default=None, primary_key=True)
    analysis_id: int = Field(foreign_key="analyses.id", index=True)

    type: TermType
    value: str | None = Field(default=None)
    numeric_value: Decimal | None = Field(
        default=None, max_digits=14, decimal_places=2
    )
    status: TermStatus = Field(default=TermStatus.MISSING)
    confidence: float = Field(default=0.0)

    # Message indices (not database ids) this value came from.
    source_message_ids: list[int] = Field(
        default_factory=list, sa_column=Column(JSON)
    )

    revision_state: RevisionState = Field(default=RevisionState.NONE)
    # [{"value": "45000", "source_message_ids": [9]}, ...], oldest first.
    revision_history: list[dict] = Field(
        default_factory=list, sa_column=Column(JSON)
    )

    # Set by the grounding check: the value was found in the messages it
    # cites. A term that fails this is dropped before it reaches the UI,
    # which is how "hallucinated terms" stays at zero.
    source_verified: bool = Field(default=False)


class Flag(SQLModel, table=True):
    """One risk finding. Every flag carries the statutory reason, shown
    inline in the UI rather than only in the README."""

    __tablename__ = "flags"

    id: int | None = Field(default=None, primary_key=True)
    analysis_id: int = Field(foreign_key="analyses.id", index=True)

    term_type: TermType
    severity: Severity
    title: str
    why_it_matters: str

    statute: str  # "Indian Contract Act, 1872"
    section: str  # "s.29"
    statute_gist: str  # plain-language, from data/legal_refs.json

    suggested_question: str | None = Field(default=None)
    source_message_ids: list[int] = Field(
        default_factory=list, sa_column=Column(JSON)
    )
