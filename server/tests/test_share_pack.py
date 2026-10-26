"""Share with a CA or lawyer: create, read, expire, revoke, and above all
what the public page must never contain. No LLM is called: analyses are
written straight into the database, the way test_p1_api does it."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models.analysis import Analysis, ExtractedTerm, Severity, TermStatus, TermType
from app.models.base import utcnow
from app.models.share import ShareLink

SAMPLES = Path(__file__).parents[1] / "app" / "data" / "samples"


@pytest.fixture(scope="module")
def app():
    from app.main import app as fastapi_app

    return fastapi_app


@pytest.fixture(scope="module")
def client(app):
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def anon(app):
    """A separate browser session: what a CA opens the link in."""
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


def share(client, cid: int, days: int | None = None):
    body = {} if days is None else {"days": days}
    return client.post(f"/api/evidence/{cid}/share", json=body)


def token_of(share_json: dict) -> str:
    return share_json["url"].rsplit("/", 1)[1]


def pack(anon, share_json: dict):
    return anon.get(f"/api/pack/{token_of(share_json)}")


# ------------------------------------------------------------------ create


def test_link_defaults_to_seven_days_and_has_a_long_random_token(client) -> None:
    cid = upload(client, "T01_clear_deal.txt")
    r = share(client, cid)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["url"].startswith("/pack/") and len(token_of(body)) >= 32
    assert body["revoked"] is False and body["expired"] is False and body["view_count"] == 0
    # Two links never share a token.
    assert token_of(share(client, cid).json()) != token_of(body)


def test_expiry_days_are_bounded(client) -> None:
    cid = upload(client, "T04_price_revised_twice.txt")
    assert share(client, cid, days=0).status_code == 422
    assert share(client, cid, days=31).status_code == 422
    assert share(client, cid, days=30).status_code == 201


def test_unknown_chat_is_404(client) -> None:
    assert share(client, 999999).status_code == 404


# ------------------------------------------------------------------ the pack


def test_pack_is_readable_without_any_sign_in(anon, client) -> None:
    cid = upload(client, "T05_unresolved_conflict.txt")
    s = share(client, cid).json()
    r = pack(anon, s)
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["title"] == "Evidence summary for review"
    # Not "court-ready", not a "legal pack".
    text = r.text.lower().replace("not a court-ready bundle", "")
    assert "court-ready" not in text and "legal pack" not in text
    assert any("not a court-ready" in n.lower() for n in body["notices"])
    assert any("Part B" in n for n in body["notices"])

    assert body["case"]["message_count"] > 0
    assert body["chain"]["intact"] is True
    assert body["timeline"] and all(e["verified"] for e in body["timeline"])
    assert len(body["timeline"][0]["chain_hash"]) == 64


def test_pack_headers_forbid_indexing_and_caching(anon, client) -> None:
    cid = upload(client, "T06_hinglish_numbers_in_words.txt")
    r = pack(anon, share(client, cid).json())
    assert "noindex" in r.headers["x-robots-tag"]
    assert "no-store" in r.headers["cache-control"]
    assert r.headers["referrer-policy"] == "no-referrer"


def test_part_a_party_fields_are_blank_and_statements_unticked(anon, client) -> None:
    cid = upload(client, "T10_two_deals_one_chat.txt")
    cert = pack(anon, share(client, cid).json()).json()["certificate"]
    assert cert["party_fields"]  # listed, to be completed by the party
    assert cert["statements"] and not any(s["affirmed"] for s in cert["statements"])
    values = {f["label"]: f["value"] for f in cert["integrity"]}
    assert values["Hash algorithm"] == "SHA-256" and len(values["Hash of the file as uploaded"]) == 64
    assert any("Part B" in c for c in cert["cautions"])


def test_pack_never_exposes_raw_payloads(anon, client) -> None:
    cid = upload(client, "T11_prompt_injection.txt")
    r = pack(anon, share(client, cid).json())
    assert '"actor"' not in r.text and '"user_id"' not in r.text
    assert '"payload"' not in r.text  # raw payloads are not part of the shape


def test_identifiers_in_the_chat_are_masked_everywhere(anon, client) -> None:
    cid = upload(client, "T15_pii_heavy.txt")
    add_analysis(cid, [
        term(TermType.SCOPE, "cotton bedsheets", [0, 1, 2, 3, 4, 5, 6]),
        term(TermType.PARTY, "Call 9900011122 for delivery", [3]),
        term(TermType.PRICE, "195000 plus GST", [5]),
    ])
    r = pack(anon, share(client, cid).json())
    assert r.status_code == 200
    for raw in ("98450 12345", "9900011122", "ABCDE1234F", "29ABCDE1234F1Z5",
                "1234 5678 9012", "accounts@kaverimills.in", "kaverimills@okaxis"):
        assert raw not in r.text, raw
    body = r.json()
    assert body["identifiers_hidden"] >= 6
    # The cited message is shown, with a token where the number was.
    assert any("<PHONE_" in s["body"] for s in body["sources"] if s["index"] == 3)
    assert any("<PHONE_" in (t["value"] or "") for t in body["summary"]["terms"])


def test_hashes_are_not_altered_by_masking(anon, client) -> None:
    """A hex digest can contain a long digit run an identifier pattern would
    mask. The pack must show the hash exactly as the chain computed it."""
    cid = upload(client, "T15_pii_heavy.txt")
    mine = client.get(f"/api/evidence/{cid}").json()["events"]
    body = pack(anon, share(client, cid).json()).json()
    assert [e["chain_hash"] for e in body["timeline"]] == [e["chain_hash"] for e in mine]
    assert [e["payload_sha256"] for e in body["timeline"]] == [e["payload_sha256"] for e in mine]
    certified = {f["label"]: f["value"] for f in body["certificate"]["integrity"]}
    assert certified["Hash of the file as uploaded"] == client.get(f"/api/conversations/{cid}").json()["content_sha256"]


def test_summary_carries_terms_flags_and_their_source_messages(anon, client) -> None:
    cid = upload(client, "T14_price_revised_back.txt")
    add_analysis(cid, [term(TermType.PRICE, "4500 each", [2])])
    body = pack(anon, share(client, cid).json()).json()
    assert body["summary"]["readiness"] == "yellow"
    assert any(t["type"] == "price" and t["source_message_ids"] == [2] for t in body["summary"]["terms"])
    assert [s["index"] for s in body["sources"]] == [2]


def test_no_analysis_still_gives_a_pack_without_a_summary(anon, client) -> None:
    cid = upload(client, "T20_no_deal_small_talk.txt")
    body = pack(anon, share(client, cid).json()).json()
    assert body["summary"] is None and body["agreement"] is None
    assert body["timeline"] and body["certificate"]


def test_agreement_and_who_acknowledged_it(anon, client) -> None:
    cid = upload(client, "T16_ambiguous_dates.txt")
    add_analysis(cid, [term(TermType.PRICE, "4500 each", [2]), term(TermType.SCOPE, "chairs", [0])])
    gen = client.post(f"/api/agreements/{cid}/generate", json={})
    assert gen.status_code == 201, gen.text
    agreement_id = gen.json()["id"]

    send = client.post(f"/api/agreements/{agreement_id}/send")
    assert send.status_code == 200, send.text
    confirm_token = send.json()["confirm_url"].rsplit("/", 1)[1]
    clauses = [c for c in gen.json()["clauses"] if not c["is_placeholder"]]
    answered = anon.post(
        f"/api/confirm/{confirm_token}",
        json={"typed_name": "Priya Sharma", "read_confirmation": True,
              "answers": [{"clause_id": c["id"], "action": "agree"} for c in clauses]},
    )
    assert answered.status_code == 200, answered.text

    body = pack(anon, share(client, cid).json()).json()
    assert body["agreement"]["version"] == 1
    assert body["agreement"]["clauses"] and len(body["agreement"]["clauses_hash"]) == 64
    assert {r["typed_name"] for r in body["agreement"]["responses"]} == {"Priya Sharma"}
    assert "not electronic signatures" in body["agreement"]["acknowledgement_note"]
    # The event that recorded it is in the timeline, in words, without a payload.
    assert any("Priya Sharma" in e["summary"] for e in body["timeline"])


def test_viewing_is_counted_for_the_owner(anon, client) -> None:
    cid = upload(client, "T17_us_date_format.txt")
    s = share(client, cid).json()
    pack(anon, s)
    pack(anon, s)
    listed = {x["id"]: x for x in client.get(f"/api/evidence/{cid}/shares").json()}
    assert listed[s["id"]]["view_count"] == 2 and listed[s["id"]]["last_viewed_at"]


def test_a_broken_chain_shows_broken_from_the_altered_event_on(anon, client) -> None:
    cid = upload(client, "T02_vague_timing.txt")
    assert client.post(f"/api/evidence/{cid}/_tamper?sequence=0").status_code == 200

    body = pack(anon, share(client, cid).json()).json()
    assert body["chain"]["intact"] is False
    assert body["chain"]["broken_at_sequence"] == 0
    assert body["timeline"][0]["verified"] is False


# ------------------------------------------------------------ expiry and off


def test_unknown_token_is_404(anon) -> None:
    r = anon.get("/api/pack/not-a-real-token")
    assert r.status_code == 404 and "not valid" in r.json()["detail"]


def test_revoked_link_stops_working_immediately(anon, client) -> None:
    cid = upload(client, "T18_format_torture.txt")
    s = share(client, cid).json()
    assert pack(anon, s).status_code == 200

    off = client.post(f"/api/evidence/{cid}/share/{s['id']}/revoke")
    assert off.status_code == 200 and off.json()["revoked"] is True
    gone = pack(anon, s)
    assert gone.status_code == 410 and "turned this link off" in gone.json()["detail"]
    # Revoking twice is harmless.
    assert client.post(f"/api/evidence/{cid}/share/{s['id']}/revoke").status_code == 200


def test_expired_link_is_gone(anon, client) -> None:
    from app.core.db import engine

    cid = upload(client, "T12_group_chat.txt")
    s = share(client, cid).json()
    with Session(engine) as db:
        row = db.exec(select(ShareLink).where(ShareLink.id == s["id"])).one()
        row.expires_at = utcnow() - timedelta(minutes=1)
        db.add(row)
        db.commit()
    r = pack(anon, s)
    assert r.status_code == 410 and "expired" in r.json()["detail"]
    listed = {x["id"]: x for x in client.get(f"/api/evidence/{cid}/shares").json()}
    assert listed[s["id"]]["expired"] is True


def test_revoke_with_a_mismatched_chat_id_is_404(client) -> None:
    a = upload(client, "T13_sarcastic_ok.txt")
    b = upload(client, "T03_price_missing.txt")
    s = share(client, a).json()
    assert client.post(f"/api/evidence/{b}/share/{s['id']}/revoke").status_code == 404


def test_active_link_cap(client) -> None:
    cid = upload(client, "T21_one_sided_notes.txt")
    codes = [share(client, cid).status_code for _ in range(11)]
    assert codes[:10] == [201] * 10 and codes[10] == 409
