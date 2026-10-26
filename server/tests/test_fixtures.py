"""Checks every labelled chat's deterministic expectations.

The "parser" block of each .expected.json is checked here, on every test
run, with no AI model involved: message counts, participants, date format,
attachments, warnings, and exactly what the privacy mask hides. Invalid
inputs are sent through the real upload endpoint and must fail with the
labelled status and a plain message.

The model-dependent "expected" block is checked by tests/run_eval.py.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services import pii_masker
from app.services.chat_parser import ChatParseError, MessageKind, parse_whatsapp_export

CHATS = Path(__file__).parent / "fixtures" / "chats"
LABELS = sorted(CHATS.glob("T*.expected.json"))
INVALID = json.loads((CHATS / "invalid.expected.json").read_text(encoding="utf-8"))


def _label(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse(label: dict):
    raw = (CHATS / label["file"]).read_bytes().decode("utf-8-sig")
    return parse_whatsapp_export(raw)


def test_every_labelled_chat_has_a_file() -> None:
    assert len(LABELS) >= 20
    for path in LABELS:
        assert (CHATS / _label(path)["file"]).exists(), path.name


@pytest.mark.parametrize("path", LABELS, ids=lambda p: p.name.split("_")[0])
def test_parser_expectations(path: Path) -> None:
    label = _label(path)
    want = label["parser"]
    result = _parse(label)
    msgs = result.messages

    assert result.participants == want["participants"]
    assert result.date_order.value == want["date_order"]

    if "messages" in want:
        assert len(msgs) == want["messages"]
    if "messages_at_least" in want:
        assert len(msgs) >= want["messages_at_least"]

    attachments = sum(m.kind is MessageKind.ATTACHMENT for m in msgs)
    if "attachments" in want:
        assert attachments == want["attachments"]
    if "attachments_at_least" in want:
        assert attachments >= want["attachments_at_least"]
    if "system_messages" in want:
        assert sum(m.kind is MessageKind.SYSTEM for m in msgs) == want["system_messages"]
    if "deleted" in want:
        assert sum(m.kind is MessageKind.DELETED for m in msgs) == want["deleted"]

    for fragment in want.get("warnings_contain", []):
        assert any(fragment in w for w in result.warnings), f"no warning containing {fragment!r}"

    if "multiline_contains" in want:
        assert any(want["multiline_contains"] in m.body and "\n" in m.body for m in msgs)
    if "first_timestamp" in want:
        assert msgs[0].timestamp.isoformat() == want["first_timestamp"]
    if "last_hour" in want:
        assert msgs[-1].timestamp.hour == want["last_hour"]

    # Privacy: exactly the labelled identifiers are hidden, and nothing leaks.
    joined = "\n".join(m.body for m in msgs)
    masked = pii_masker.pseudonymise(joined)
    assert masked.masked_counts == want.get("masked", {})
    assert not pii_masker.contains_identifier(masked.text)


def test_pii_fixture_keeps_prices_and_order_numbers() -> None:
    label = _label(CHATS / "T15_pii_heavy.expected.json")
    text = pii_masker.pseudonymise("\n".join(m.body for m in _parse(label).messages)).text
    assert "1234567890" in text  # an order number is not a phone number
    assert "195000" in text and "650" in text  # prices are never masked


@pytest.mark.parametrize("case", [x for x in INVALID if x["file"].endswith(".txt")], ids=lambda x: x["id"])
def test_invalid_text_inputs_fail_in_the_parser(case: dict) -> None:
    path = CHATS / case["file"]
    if not path.exists():
        pytest.skip("large fixture not generated; run python -m tests.fixtures.build_fixtures")
    if case["error"]["status"] == 413:
        pytest.skip("size limit is enforced by the upload endpoint, tested below")
    with pytest.raises(ChatParseError) as err:
        parse_whatsapp_export(path.read_bytes().decode("utf-8", errors="replace"), max_messages=5_000)
    assert case["error"]["message_contains"].lower() in str(err.value).lower()


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.mark.parametrize("case", INVALID, ids=lambda x: x["id"])
def test_invalid_inputs_fail_safely_through_the_api(client, case: dict) -> None:
    path = CHATS / case["file"]
    if not path.exists():
        pytest.skip("large fixture not generated; run python -m tests.fixtures.build_fixtures")
    response = client.post(
        "/api/conversations",
        files={"file": (Path(case["file"]).name, path.read_bytes(), "text/plain")},
    )
    assert response.status_code == case["error"]["status"]
    detail = response.json()["detail"]
    assert case["error"]["message_contains"].lower() in detail.lower()
    assert "Traceback" not in detail
