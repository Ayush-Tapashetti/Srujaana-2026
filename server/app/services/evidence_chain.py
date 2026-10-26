"""SHA-256 hash chain (F6).

Each event's hash includes the previous event's hash:

    h_n = SHA256(h_(n-1) || SHA256(payload) || timestamp)

Change any stored event and every link after it stops matching, so history
cannot be quietly edited. Verification reports the FIRST broken sequence
number rather than a bare boolean, which is what makes the tamper demo
legible on screen ("broken at event 3", not just a red light).

Honest limit (D4), stated in the UI and the README: this proves nothing
changed since upload. It cannot prove the chat was genuine before upload.

Legal anchor: BSA 2023 s.63(4) and the Schedule, Part A, require the hash
value and algorithm to be disclosed. We compute exactly that. Part B needs
an expert and the app does not attempt it.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

GENESIS = "0" * 64
ALGORITHM = "SHA-256"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_hash(payload: dict[str, Any]) -> str:
    """Hash a payload reproducibly.

    Sorted keys and no whitespace, so the same payload hashes identically on
    any machine and any Python version. Without this, verification fails on a
    teammate's laptop for no visible reason.
    """
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return sha256_bytes(blob.encode("utf-8"))


def _canonical_time(moment: datetime) -> str:
    """One text form for a moment, whatever the database hands back.

    Postgres may return the same instant in another timezone, or without
    one. Hashing the raw isoformat() would then make an untouched chain
    verify as broken. Normalise to UTC first; a naive value is taken as UTC,
    because every timestamp this app writes is UTC.
    """
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).isoformat(timespec="microseconds")


def link_hash(prev_hash: str, payload_sha256: str, occurred_at: datetime) -> str:
    material = f"{prev_hash}|{payload_sha256}|{_canonical_time(occurred_at)}"
    return sha256_bytes(material.encode("utf-8"))


class ChainEvent(Protocol):
    """Structural type: anything with these fields can be verified."""

    sequence: int
    occurred_at: datetime
    payload: dict[str, Any]
    payload_sha256: str
    prev_hash: str
    chain_hash: str


@dataclass(slots=True)
class VerificationResult:
    intact: bool
    checked: int
    broken_at_sequence: int | None = None
    reason: str | None = None


def verify_chain(events: list[ChainEvent]) -> VerificationResult:
    """Recompute every link and report the first failure."""
    ordered = sorted(events, key=lambda e: e.sequence)
    expected_prev = GENESIS

    for position, event in enumerate(ordered):
        if event.sequence != position:
            return VerificationResult(
                intact=False,
                checked=position,
                broken_at_sequence=event.sequence,
                reason="An event is missing or out of order.",
            )

        if event.prev_hash != expected_prev:
            return VerificationResult(
                intact=False,
                checked=position,
                broken_at_sequence=event.sequence,
                reason="This event does not link to the one before it.",
            )

        if canonical_hash(event.payload) != event.payload_sha256:
            return VerificationResult(
                intact=False,
                checked=position,
                broken_at_sequence=event.sequence,
                reason="The contents of this event changed after it was recorded.",
            )

        if link_hash(event.prev_hash, event.payload_sha256, event.occurred_at) != (
            event.chain_hash
        ):
            return VerificationResult(
                intact=False,
                checked=position,
                broken_at_sequence=event.sequence,
                reason="The chain hash does not match the recorded values.",
            )

        expected_prev = event.chain_hash

    return VerificationResult(intact=True, checked=len(ordered))


# --------------------------------------------------------------------------
# The one function here that touches the database. Everything above is pure
# so it can be unit-tested without Postgres.
# --------------------------------------------------------------------------


def append_event(
    session: Any,
    *,
    conversation_id: int,
    event_type: Any,
    payload: dict[str, Any],
) -> Any:
    """Append one event to a conversation's chain.

    The caller commits. Upload and its first evidence event must land in the
    same transaction, so a crash can never leave a conversation with no
    genesis event.
    """
    from sqlmodel import select

    from app.models.base import utcnow
    from app.models.evidence import EvidenceEvent

    previous = session.exec(
        select(EvidenceEvent)
        .where(EvidenceEvent.conversation_id == conversation_id)
        .order_by(EvidenceEvent.sequence.desc())
        .limit(1)
    ).first()

    sequence = 0 if previous is None else previous.sequence + 1
    prev_hash = GENESIS if previous is None else previous.chain_hash

    occurred_at = utcnow()
    payload_sha256 = canonical_hash(payload)

    event = EvidenceEvent(
        conversation_id=conversation_id,
        sequence=sequence,
        type=event_type,
        occurred_at=occurred_at,
        payload=payload,
        payload_sha256=payload_sha256,
        prev_hash=prev_hash,
        chain_hash=link_hash(prev_hash, payload_sha256, occurred_at),
    )
    session.add(event)
    return event
