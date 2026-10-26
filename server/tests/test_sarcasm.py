"""Sarcasm guard: a sarcastic "ok" must not count as agreement, and a
genuine one must keep working. No AI model and no database are involved."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from app.models.analysis import RevisionState, Severity, TermStatus, TermType
from app.models.conversation import Message
from app.services import checklist_engine, extractor, sarcasm
from app.services.chat_parser import MessageKind, parse_whatsapp_export

SAMPLES = Path(__file__).parents[1] / "app" / "data" / "samples"
CHATS = Path(__file__).parent / "fixtures" / "chats"

SARCASTIC = [
    "ok sure, and I'll deliver them on a golden chariot also 🙄",
    "Yeah right 😒",
    "oh sure, 3500. dream on",
    "ok /s",
    "Sure sir, and I'll also give them free of cost, on the moon",
    "haan haan bilkul, aur main chaand pe delivery bhi kar dunga",
    "Ok sure while you're at it take my shop too lol",
    "wow ok great price 🙄",
    "Fine... 🙃",
    "mazak hai kya sir",
    "good luck with that",
    "ok sure, and I will also paint them gold too 😂",
]

GENUINE = [
    "ok sir",
    "Ok sure",
    "Yes sir, confirmed. Payment within 30 days",
    "Theek hai 180 chalega",
    "👍",
    "ok, and I'll send the invoice tomorrow too",
    "Fine, 4500 and 30 days after delivery as before",
    "Done sir, will deliver on 15 Sept",
    "haan ji",
    "Ok 4200 with full advance",
    "Sure, I will also include GST invoice",
    "Production has started sir",
    "okay 😊",
    "ok sir, and I'll deliver on Friday also",
    "Agreed 🙏",
]


@pytest.mark.parametrize("text", SARCASTIC)
def test_sarcastic_replies_are_caught(text: str) -> None:
    assert sarcasm.looks_sarcastic(text), sarcasm.assess(text)


@pytest.mark.parametrize("text", GENUINE)
def test_genuine_replies_are_not_held_back(text: str) -> None:
    assert not sarcasm.looks_sarcastic(text), sarcasm.assess(text)


def test_one_weak_signal_alone_is_not_enough() -> None:
    # A single medium signal must never decide on its own.
    verdict = sarcasm.assess("ok, and I'll send the invoice tomorrow too")
    assert verdict.score < sarcasm.THRESHOLD


def test_empty_reply_is_not_sarcastic() -> None:
    assert not sarcasm.looks_sarcastic("")
    assert not sarcasm.looks_sarcastic("   ")


def test_no_sample_chat_message_other_than_t13_is_flagged() -> None:
    """The guard must not turn any other demo chat's genuine "ok" Red."""
    flagged: list[tuple[str, str]] = []
    for path in sorted(SAMPLES.glob("*.txt")):
        if path.name.startswith("T13"):
            continue
        for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            match = re.match(r"^.*? - [^:]+: (.*)$", line)
            if match and sarcasm.looks_sarcastic(match.group(1)):
                flagged.append((path.name, match.group(1)))
    assert flagged == []


# ---------------------------------------------------------------- settlement


def test_accepts_plain_ok_but_not_sarcastic_ok() -> None:
    assert extractor._accepts("ok sir", "3500 per chair")
    assert extractor._accepts("Theek hai 3500", "3500 per chair")
    assert not extractor._accepts("ok sure, and I'll deliver them on a golden chariot also 🙄", "3500 per chair")


def test_repeating_the_number_sarcastically_is_not_acceptance() -> None:
    assert not extractor._accepts("Sure, 3500 🙄", "3500 per chair")


def _messages(path: Path) -> list[Message]:
    parsed = parse_whatsapp_export(path.read_bytes().decode("utf-8-sig"))
    return [
        Message(conversation_id=0, index=m.index, timestamp=m.timestamp, sender=m.sender, body=m.body, kind=m.kind)
        for m in parsed.messages
    ]


def _rules_only(messages: list[Message]):
    filled, _ = extractor.fill_gaps_with_rules([], messages)
    terms = extractor.resolve_terms(filled, messages)
    precise = extractor.anchor_relative_dates(terms, messages)
    extractor.mark_obviously_vague(terms, precise)
    return terms, checklist_engine.evaluate(terms)


def test_t13_price_cut_is_not_settled_and_says_why() -> None:
    terms, result = _rules_only(_messages(SAMPLES / "T13_sarcastic_ok.txt"))

    price = next(t for t in terms if t.type is TermType.PRICE)
    assert "3500" in price.value
    assert price.revision_state is RevisionState.UNRESOLVED
    assert price.status is TermStatus.CONFLICTED
    assert price.sarcastic_reply_index == 3  # the 🙄 message

    assert result.readiness is Severity.RED
    assert result.can_send is False

    flag = next(f for f in result.flags if f.term_type is TermType.PRICE)
    assert flag.severity is Severity.RED
    assert "sarcasm" in flag.title.lower()
    assert 3 in flag.source_message_ids and 2 in flag.source_message_ids
    # It must not claim the other side said nothing: they did reply.
    assert "never replied" not in flag.why_it_matters
    assert flag.suggested_question and "yes or no" in flag.suggested_question


def test_t13_label_matches_behaviour() -> None:
    label = json.loads((CHATS / "T13_sarcastic_ok.expected.json").read_text(encoding="utf-8"))
    assert label["known_failure"] is False
    assert label["expected"]["overall"] == "red"
    assert label["expected"]["terms"]["price"]["status"] == "conflicted"


def test_a_genuine_revision_is_still_settled() -> None:
    """T14 revises the price and the seller really agrees: still settled."""
    terms, _ = _rules_only(_messages(SAMPLES / "T14_price_revised_back.txt"))
    price = next(t for t in terms if t.type is TermType.PRICE)
    assert price.revision_state is RevisionState.SETTLED
    assert price.sarcastic_reply_index is None


def test_unanswered_revision_keeps_its_original_flag_wording() -> None:
    """T05's seller changes the subject; that is NOT sarcasm and must keep the
    original 'never replied' explanation."""
    terms, result = _rules_only(_messages(SAMPLES / "T05_unresolved_conflict.txt"))
    price = next(t for t in terms if t.type is TermType.PRICE)
    assert price.sarcastic_reply_index is None
    flag = next(f for f in result.flags if f.term_type is TermType.PRICE and f.severity is Severity.RED)
    assert "never confirmed" in flag.title
