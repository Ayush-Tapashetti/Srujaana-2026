"""Hash chain tests, including every tamper case in TEST_PLAN section 7.

These use a plain dataclass rather than the SQLModel table, so the chain
logic is tested without Postgres.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from app.services.evidence_chain import (
    GENESIS,
    canonical_hash,
    link_hash,
    verify_chain,
)

BASE = datetime(2026, 10, 24, 9, 0, tzinfo=timezone.utc)


@dataclass
class FakeEvent:
    sequence: int
    occurred_at: datetime
    payload: dict[str, Any]
    payload_sha256: str = ""
    prev_hash: str = ""
    chain_hash: str = ""


def build_chain(count: int = 4) -> list[FakeEvent]:
    events: list[FakeEvent] = []
    prev = GENESIS
    for i in range(count):
        occurred_at = BASE + timedelta(minutes=i)
        payload = {"step": i, "note": f"event {i}"}
        payload_hash = canonical_hash(payload)
        chain = link_hash(prev, payload_hash, occurred_at)
        events.append(
            FakeEvent(
                sequence=i,
                occurred_at=occurred_at,
                payload=payload,
                payload_sha256=payload_hash,
                prev_hash=prev,
                chain_hash=chain,
            )
        )
        prev = chain
    return events


class TestCanonicalHash:
    def test_key_order_does_not_change_the_hash(self) -> None:
        assert canonical_hash({"a": 1, "b": 2}) == canonical_hash({"b": 2, "a": 1})

    def test_any_change_changes_the_hash(self) -> None:
        assert canonical_hash({"a": 1}) != canonical_hash({"a": 2})

    def test_same_instant_in_another_timezone_gives_same_link(self) -> None:
        """Postgres may hand back the same moment in a different zone."""
        from datetime import timedelta as td
        from datetime import timezone as tz

        ist = tz(td(hours=5, minutes=30))
        assert link_hash(GENESIS, "x", BASE) == link_hash(GENESIS, "x", BASE.astimezone(ist))

    def test_naive_time_is_read_as_utc(self) -> None:
        assert link_hash(GENESIS, "x", BASE) == link_hash(GENESIS, "x", BASE.replace(tzinfo=None))

    def test_hash_is_64_hex_characters(self) -> None:
        digest = canonical_hash({"a": 1})
        assert len(digest) == 64
        assert all(c in "0123456789abcdef" for c in digest)


class TestIntactChain:
    def test_valid_chain_verifies(self) -> None:
        result = verify_chain(build_chain())
        assert result.intact is True
        assert result.checked == 4

    def test_empty_chain_is_intact(self) -> None:
        result = verify_chain([])
        assert result.intact is True
        assert result.checked == 0

    def test_single_event_links_to_genesis(self) -> None:
        events = build_chain(1)
        assert events[0].prev_hash == GENESIS
        assert verify_chain(events).intact is True

    def test_order_of_the_input_list_does_not_matter(self) -> None:
        events = build_chain()
        assert verify_chain(list(reversed(events))).intact is True


class TestTamperDetection:
    def test_tamper_with_the_first_event(self) -> None:
        events = build_chain()
        events[0].payload["note"] = "edited"
        result = verify_chain(events)
        assert result.intact is False
        assert result.broken_at_sequence == 0

    def test_tamper_with_a_middle_event(self) -> None:
        events = build_chain()
        events[2].payload["note"] = "edited"
        result = verify_chain(events)
        assert result.intact is False
        assert result.broken_at_sequence == 2
        assert "changed" in result.reason

    def test_tamper_with_the_last_event(self) -> None:
        events = build_chain()
        events[-1].payload["note"] = "edited"
        assert verify_chain(events).broken_at_sequence == 3

    def test_deleting_an_event_is_detected(self) -> None:
        events = build_chain()
        del events[2]
        result = verify_chain(events)
        assert result.intact is False
        assert "missing or out of order" in result.reason

    def test_reordering_two_events_is_detected(self) -> None:
        events = build_chain()
        events[1].sequence, events[2].sequence = 2, 1
        assert verify_chain(events).intact is False

    def test_rewriting_a_timestamp_is_detected(self) -> None:
        events = build_chain()
        events[2].occurred_at = BASE + timedelta(days=5)
        result = verify_chain(events)
        assert result.intact is False
        assert result.broken_at_sequence == 2

    def test_recomputing_one_payload_hash_still_breaks_the_link(self) -> None:
        """A careful attacker fixes payload_sha256 after editing the payload.
        The chain_hash of that event, and every event after it, still fails."""
        events = build_chain()
        events[1].payload["note"] = "edited"
        events[1].payload_sha256 = canonical_hash(events[1].payload)
        result = verify_chain(events)
        assert result.intact is False
        assert result.broken_at_sequence == 1

    def test_appending_a_forged_event_is_detected(self) -> None:
        events = build_chain()
        events.append(
            FakeEvent(
                sequence=4,
                occurred_at=BASE + timedelta(minutes=4),
                payload={"step": 4},
                payload_sha256=canonical_hash({"step": 4}),
                prev_hash=GENESIS,  # does not follow event 3
                chain_hash="0" * 64,
            )
        )
        result = verify_chain(events)
        assert result.intact is False
        assert result.broken_at_sequence == 4
