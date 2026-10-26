"""D6 end to end: no identifier ever reaches an LLM prompt.

The LLM is replaced with a fake that records every prompt it is sent and
answers with values written in TOKENS, the way a real model would see them.
That proves both halves of the promise:

  1. nothing the masker recognises appears in any prompt, and
  2. token values are restored before grounding, so a contact detail the
     model reports as <PHONE_1> still grounds against the real message.
"""

import json
from datetime import datetime
from pathlib import Path

import pytest

from app.models.analysis import TermType
from app.models.conversation import Message
from app.services import extractor, pii_masker
from app.services.chat_parser import parse_whatsapp_export
from app.services.llm_service import LlmResponse, Provider

SAMPLE = Path(__file__).parents[1] / "app" / "data" / "samples" / "T15_pii_heavy.txt"


def load_messages() -> list[Message]:
    parsed = parse_whatsapp_export(SAMPLE.read_text(encoding="utf-8"))
    return [
        Message(
            conversation_id=1,
            index=m.index,
            timestamp=m.timestamp,
            sender=m.sender,
            body=m.body,
            kind=m.kind,
        )
        for m in parsed.messages
    ]


class FakeLlm:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def __call__(self, session, *, system: str, prompt: str, use_cache: bool = True) -> LlmResponse:  # noqa: ANN001
        self.prompts.append(system + "\n" + prompt)
        if "Which are vague" in prompt:
            body = {"vague_types": [], "reasons": {}}
        else:
            phone_token = next(t for t in ("<PHONE_1>", "<PHONE_2>") if t in prompt)
            body = {
                "mentions": [
                    {"type": "party", "value": "Meena Textiles", "source_message_ids": [0], "confidence": 0.9},
                    {"type": "party", "value": f"Kaveri Mills, {phone_token}", "source_message_ids": [3], "confidence": 0.8},
                    {"type": "price", "value": "650 each plus GST", "source_message_ids": [0], "confidence": 0.9},
                ]
            }
        return LlmResponse(text=json.dumps(body), model="fake", provider=Provider.GROQ)


@pytest.fixture
def fake_llm(monkeypatch: pytest.MonkeyPatch) -> FakeLlm:
    fake = FakeLlm()
    monkeypatch.setattr(extractor, "complete_json", fake)
    return fake


def test_no_identifier_reaches_any_prompt(fake_llm: FakeLlm) -> None:
    extractor.extract(None, load_messages())  # type: ignore[arg-type]
    assert len(fake_llm.prompts) >= 2  # extraction + vagueness
    for prompt in fake_llm.prompts:
        conversation = prompt.split("Conversation:", 1)[-1]
        assert not pii_masker.contains_identifier(conversation), conversation
        for leaked in ("98450 12345", "9900011122", "ABCDE1234F", "1234 5678 9012", "kaverimills@okaxis", "accounts@kaverimills.in"):
            assert leaked not in conversation


def test_token_values_are_restored_before_grounding(fake_llm: FakeLlm) -> None:
    result = extractor.extract(None, load_messages())  # type: ignore[arg-type]
    parties = [t.value for t in result.terms if t.type is TermType.PARTY]
    assert any("+91 98450 12345" in p for p in parties), parties
    assert not result.dropped_ungrounded
    assert all("<PHONE" not in t.value for t in result.terms)


def test_tokens_are_consistent_across_messages() -> None:
    texts = ["call 9900011122", "again 9900011122", "email a@b.in"]
    masked, result = pii_masker.pseudonymise_many(texts)
    assert masked[0].endswith("<PHONE_1>") and masked[1].endswith("<PHONE_1>")
    assert masked[2] == "email <EMAIL_1>"
    assert [result.restore(m) for m in masked] == texts


def test_transcript_without_mask_is_unchanged() -> None:
    msgs = [Message(conversation_id=1, index=0, timestamp=datetime(2024, 1, 1), sender="A", body="call 9900011122", kind="text")]
    assert "9900011122" in extractor.build_transcript(msgs)
    mask = extractor.conversation_mask(msgs)
    assert "<PHONE_1>" in extractor.build_transcript(msgs, mask)
