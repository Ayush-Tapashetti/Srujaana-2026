"""P1 endpoints through the API: certificate draft, masked preview, MSME
check, revision reply index, and the evaluation page. No LLM is called:
analyses are written straight into the database the way extraction would.
"""

from pathlib import Path

import pytest
from sqlmodel import Session

from app.models.analysis import Analysis, ExtractedTerm, RevisionState, Severity, TermStatus, TermType

SAMPLES = Path(__file__).parents[1] / "app" / "data" / "samples"


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c


def upload(client, name: str) -> int:
    raw = (SAMPLES / name).read_bytes()
    r = client.post("/api/conversations", files={"file": (name, raw, "text/plain")})
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


def add_analysis(cid: int, terms: list[ExtractedTerm]) -> None:
    from app.core.db import engine

    with Session(engine) as s:
        a = Analysis(conversation_id=cid, model_used="test", prompt_version="test", from_cache=False, readiness=Severity.YELLOW)
        s.add(a)
        s.flush()
        for t in terms:
            t.analysis_id = a.id
            s.add(t)
        s.commit()


def term(t: TermType, value: str, ids: list[int], **kw) -> ExtractedTerm:
    return ExtractedTerm(type=t, value=value, status=kw.pop("status", TermStatus.CLEAR), confidence=0.9,
                         source_message_ids=ids, source_verified=True, **kw)


def test_masked_preview_hides_every_identifier(client) -> None:
    cid = upload(client, "T15_pii_heavy.txt")
    body = client.get(f"/api/conversations/{cid}/masked-preview").json()
    assert body["leak_check_passed"] is True
    assert body["total"] >= 6
    sent = " ".join(line["sent"] or "" for line in body["lines"])
    assert "98450 12345" not in sent and "ABCDE1234F" not in sent
    assert "<PHONE_1>" in sent
    assert any(line["masked"] for line in body["lines"])


def test_masked_preview_withholds_injection(client) -> None:
    cid = upload(client, "T11_prompt_injection.txt")
    lines = client.get(f"/api/conversations/{cid}/masked-preview").json()["lines"]
    assert any(line["withheld"] for line in lines)


def test_certificate_draft_prefills_and_never_affirms(client) -> None:
    cid = upload(client, "T01_clear_deal.txt")
    body = client.get(f"/api/evidence/{cid}/certificate-draft").json()
    values = {f["label"]: f["value"] for f in body["record"] + body["integrity"]}
    assert values["Hash algorithm"] == "SHA-256"
    assert len(values["Hash of the file as uploaded"]) == 64
    assert values["Chain check"] == "Intact"
    assert body["statements"] and not any(s["affirmed"] for s in body["statements"])
    assert any("Part B" in c for c in body["cautions"])


def test_certificate_draft_404(client) -> None:
    assert client.get("/api/evidence/999999/certificate-draft").status_code == 404


def test_msme_check_only_flags_on_yes(client) -> None:
    cid = upload(client, "T22_msme_60_day_terms.txt")
    add_analysis(cid, [term(TermType.PAYMENT_DUE, "within 60 days of delivery", [2])])

    yes = client.get(f"/api/conversations/{cid}/msme-check", params={"supplier_is_micro_or_small": "yes"}).json()
    assert yes["exceeds_limit"] is True and yes["period_days"] == 60
    assert yes["flag"]["severity"] == "yellow" and yes["flag"]["section"] == "s.15"

    no = client.get(f"/api/conversations/{cid}/msme-check", params={"supplier_is_micro_or_small": "no"}).json()
    assert no["flag"] is None and "does not apply" in no["note"]

    unsure = client.get(f"/api/conversations/{cid}/msme-check", params={"supplier_is_micro_or_small": "unsure"}).json()
    assert unsure["flag"] is None and "Udyam" in unsure["note"]

    # Advisory only: readiness is untouched.
    assert client.get(f"/api/conversations/{cid}/analysis").json()["readiness"] == "yellow"


def test_msme_check_rejects_bad_answer(client) -> None:
    cid = upload(client, "T22_msme_60_day_terms.txt")
    assert client.get(f"/api/conversations/{cid}/msme-check", params={"supplier_is_micro_or_small": "maybe"}).status_code == 422


def test_revision_reply_index_is_computed_at_read_time(client) -> None:
    cid = upload(client, "T05_unresolved_conflict.txt")
    # T05: Ravi proposes 4200 in message 6; Sunrise's first reply is 9
    # ("Production has started sir"), which the s.62 rule judged.
    add_analysis(cid, [term(TermType.PRICE, "4200 each", [6], status=TermStatus.CONFLICTED,
                            revision_state=RevisionState.UNRESOLVED,
                            revision_history=[{"value": "4500", "source_message_ids": [2]}])])
    price = next(t for t in client.get(f"/api/conversations/{cid}/analysis").json()["terms"] if t["type"] == "price")
    assert price["response_message_index"] == 9


def test_no_revision_means_no_reply_index(client) -> None:
    cid = upload(client, "T01_clear_deal.txt")
    add_analysis(cid, [term(TermType.PRICE, "4500", [2])])
    price = next(t for t in client.get(f"/api/conversations/{cid}/analysis").json()["terms"] if t["type"] == "price")
    assert price["response_message_index"] is None


def test_evaluation_page_runs_live_checks(client) -> None:
    body = client.get("/api/eval").json()
    assert body["fixtures_found"] is True
    groups = {g["title"]: g for g in body["live"]}
    for g in groups.values():
        assert g["total"] > 0 and g["passed"] == g["total"], g
    assert groups["Identifiers hidden"]["total"] >= 20
