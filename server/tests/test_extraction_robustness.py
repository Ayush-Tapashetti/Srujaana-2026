"""The failures seen with a real model, replayed with a stand-in.

T06: the model reported the prices correctly, but the old s.62 rule read the
buyer's "Theek hai 180 chalega" as a NEW proposal and called it unagreed.
T04: the model returned only the two parties; every other term looked
missing. Both are now handled in code, so they pass whatever the model does.
"""

import json
from pathlib import Path

import pytest

from app.models.analysis import RevisionState, TermStatus, TermType
from app.models.conversation import Message
from app.services import checklist_engine, extractor
from app.services.chat_parser import parse_whatsapp_export
from app.services.llm_service import LlmResponse, Provider
from app.services.rule_extractor import amount_of, find_mentions, same_value
from tests.run_eval import check

CHATS = Path(__file__).parent / "fixtures" / "chats"


def load(name: str) -> list[Message]:
    raw = next(CHATS.glob(f"{name}_*.txt")).read_bytes().decode("utf-8-sig")
    return [
        Message(conversation_id=0, index=m.index, timestamp=m.timestamp, sender=m.sender, body=m.body, kind=m.kind)
        for m in parse_whatsapp_export(raw).messages
    ]


def label(name: str) -> dict:
    return json.loads(next(CHATS.glob(f"{name}_*.expected.json")).read_text())


def m(t: str, v: str, ids: list[int]) -> dict:
    return {"type": t, "value": v, "source_message_ids": ids, "confidence": 0.9}


def run(monkeypatch: pytest.MonkeyPatch, messages: list[Message], mentions: list[dict], vague: list[str] | None = None):
    def fake(session, *, system: str, prompt: str, use_cache: bool = True) -> LlmResponse:  # noqa: ANN001
        body = {"vague_types": vague or [], "reasons": {}} if "Which are vague" in prompt else {"mentions": mentions}
        return LlmResponse(text=json.dumps(body), model="stand-in", provider=Provider.GROQ)

    monkeypatch.setattr(extractor, "complete_json", fake)
    result = extractor.extract(None, messages)  # type: ignore[arg-type]
    return result, checklist_engine.evaluate(result.terms)


def as_api(result, checklist) -> dict:  # noqa: ANN001
    return {
        "readiness": checklist.readiness.value,
        "terms": [
            {"type": t.type.value, "value": t.value, "status": t.status.value,
             "revision_state": t.revision_state.value, "revision_history": t.revision_history}
            for t in result.terms
        ],
    }


# The exact mentions the real model returned for T06 (from the screenshot),
# plus the vagueness call that flagged "Parso pakka".
T06_REAL = [
    m("party", "Rahul Hardware", [0]), m("party", "Sharma Pipes", [1]),
    m("scope", "2 inch PVC pipe, 10 feet", [0]), m("quantity", "50 pieces", [0]),
    m("price", "Do sau rupaye per piece", [1]), m("price", "dedh sau", [2]),
    m("price", "180", [3]), m("price", "180", [4]),
    m("delivery_date", "Kal tak", [5]), m("delivery_date", "Parso pakka", [6]),
    m("payment_due", "Payment delivery pe cash", [6]),
]


def test_t06_buyer_accepting_180_settles_the_price(monkeypatch: pytest.MonkeyPatch) -> None:
    result, checklist = run(monkeypatch, load("T06"), T06_REAL, vague=["delivery_date"])
    price = next(t for t in result.terms if t.type is TermType.PRICE)
    assert price.revision_state is RevisionState.SETTLED and price.status is TermStatus.CLEAR
    assert price.source_message_ids == [3, 4]
    assert [r.value for r in price.revision_history] == ["Do sau rupaye per piece", "dedh sau"]
    delivery = next(t for t in result.terms if t.type is TermType.DELIVERY_DATE)
    assert delivery.status is TermStatus.CLEAR and "(= 12 Nov)" in delivery.value
    ok, problems = check(label("T06"), as_api(result, checklist))
    assert ok, problems


def test_t06_timeline_points_at_the_acceptance(monkeypatch: pytest.MonkeyPatch) -> None:
    msgs = load("T06")
    assert extractor.judged_reply_index(msgs, [3, 4]) == 4


def test_t04_model_returns_only_parties(monkeypatch: pytest.MonkeyPatch) -> None:
    result, checklist = run(monkeypatch, load("T04"), [m("party", "Kiran Events", [0]), m("party", "Lakshmi Printers", [1])])
    assert set(result.filled_by_rules) >= {"price", "scope", "delivery_date", "payment_due"}
    ok, problems = check(label("T04"), as_api(result, checklist))
    assert ok, problems


def test_t05_still_unresolved_with_rules_only(monkeypatch: pytest.MonkeyPatch) -> None:
    result, checklist = run(monkeypatch, load("T05"), [])
    ok, problems = check(label("T05"), as_api(result, checklist))
    assert ok, problems


def test_rules_never_override_the_model(monkeypatch: pytest.MonkeyPatch) -> None:
    result, _ = run(monkeypatch, load("T04"), [m("price", "52000", [7])])
    price = next(t for t in result.terms if t.type is TermType.PRICE)
    assert "price" not in result.filled_by_rules and price.revision_history == []


def test_injected_message_never_feeds_the_rules() -> None:
    msgs = load("T11")
    withheld = extractor.suspicious_indices(msgs)
    assert withheld
    assert all(set(r.source_message_ids).isdisjoint(withheld) for r in find_mentions(msgs, skip=withheld))


@pytest.mark.parametrize(
    ("text", "amount"),
    [("Do sau rupaye per piece", 200), ("dedh sau", 150), ("dhai sau", 250), ("saade teen hazaar", 3500),
     ("Rs. 1,80,000/-", 180000), ("2.5 lakh", 250000), ("52000 final", 52000), ("Theek hai 180 chalega", 180)],
)
def test_amounts_in_words_and_digits(text: str, amount: float) -> None:
    assert amount_of(text) == amount


def test_same_value_across_forms() -> None:
    assert same_value("Do sau", "200 per piece")
    assert same_value("180", "Theek hai 180 chalega")
    assert not same_value("4500 each", "4200 each")


def test_owner_proposal_still_needs_the_other_side() -> None:
    """Same value said twice by the SAME person is not acceptance."""
    msgs = load("T05")
    ment = [extractor.LlmMention(**m("price", "4500 each", [2])),
            extractor.LlmMention(**m("price", "4200 each", [6])),
            extractor.LlmMention(**m("price", "4200", [7]))]  # Ravi again, not Sunrise
    _, _, state = extractor.settle_revision(ment, msgs)
    assert state is RevisionState.UNRESOLVED
