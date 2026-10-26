"""Importing this package registers every table on SQLModel.metadata."""

from app.models.agreement import (
    Agreement,
    AgreementStatus,
    ClauseResponse,
    ConfirmationLink,
    ResponseAction,
)
from app.models.analysis import (
    CRITICAL_TERMS,
    Analysis,
    ExtractedTerm,
    Flag,
    RevisionState,
    Severity,
    TermStatus,
    TermType,
)
from app.models.conversation import Conversation, Message
from app.models.evidence import EventType, EvidenceEvent
from app.models.llm_cache import LlmCacheEntry
from app.models.share import ShareLink

__all__ = [
    "CRITICAL_TERMS",
    "Agreement",
    "AgreementStatus",
    "Analysis",
    "ClauseResponse",
    "ConfirmationLink",
    "Conversation",
    "EventType",
    "EvidenceEvent",
    "ExtractedTerm",
    "Flag",
    "LlmCacheEntry",
    "Message",
    "ResponseAction",
    "RevisionState",
    "Severity",
    "ShareLink",
    "TermStatus",
    "TermType",
]
