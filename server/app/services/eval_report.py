"""P1-5: the evaluation page, computed from the same labelled fixtures the
test suite uses.

Two halves, kept apart on purpose:

  live       parser + masking checks, run on every request. No LLM, so
             they cost nothing and cannot drift from the code.
  last run   the AI-dependent results that tests/run_eval.py writes to
             tests/eval_results.json. Shown with its timestamp and model,
             or as "not yet run". Never re-run from the web page, because
             that would spend the free-tier quota on a page view.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from app.models.conversation import Message
from app.services import extractor, pii_masker
from app.services.chat_parser import ChatParseError, MessageKind, parse_whatsapp_export

ROOT = Path(__file__).resolve().parents[2]
CHATS = ROOT / "tests" / "fixtures" / "chats"
LAST_RUN = ROOT / "tests" / "eval_results.json"


@dataclass(slots=True)
class CheckRow:
    id: str
    scenario: str
    passed: bool
    detail: str = ""
    skipped: bool = False


@dataclass(slots=True)
class LiveReport:
    parser: list[CheckRow] = field(default_factory=list)
    invalid: list[CheckRow] = field(default_factory=list)
    masking: list[CheckRow] = field(default_factory=list)
    rules: list[CheckRow] = field(default_factory=list)
    fixtures_found: bool = True


def _as_messages(parsed) -> list[Message]:  # noqa: ANN001
    return [
        Message(conversation_id=0, index=m.index, timestamp=m.timestamp,
                sender=m.sender, body=m.body, kind=m.kind)
        for m in parsed.messages
    ]


def check(label: dict, analysis: dict) -> tuple[bool, list[str]]:
    """Returns (passed, reasons for any mismatch)."""
    exp = label.get("expected") or {}
    problems: list[str] = []

    want = exp.get("overall")
    got = analysis["readiness"]
    if want == "red_or_yellow":
        if got not in ("red", "yellow"):
            problems.append(f"overall {got}, expected red or yellow")
    elif want and want != "any" and got != want:
        problems.append(f"overall {got}, expected {want}")

    by_type: dict[str, list[dict]] = {}
    for t in analysis["terms"]:
        by_type.setdefault(t["type"], []).append(t)

    for term_type, rule in exp.get("terms", {}).items():
        found = by_type.get(term_type, [])
        if rule.get("status") == "missing":
            if found:
                problems.append(f"{term_type} found ({found[0]['value']}), expected missing")
            continue
        if not found:
            problems.append(f"{term_type} missing")
            continue
        term = found[-1]
        if "status" in rule and term["status"] != rule["status"]:
            problems.append(f"{term_type} {term['status']}, expected {rule['status']}")
        if "value_contains" in rule and rule["value_contains"].lower() not in (term["value"] or "").lower():
            problems.append(f"{term_type} value '{term['value']}', expected to contain '{rule['value_contains']}'")
        if "revision_state" in rule and term["revision_state"] != rule["revision_state"]:
            problems.append(f"{term_type} revision {term['revision_state']}, expected {rule['revision_state']}")
        if "revision_count" in rule and len(term["revision_history"]) != rule["revision_count"]:
            problems.append(f"{term_type} {len(term['revision_history'])} revisions, expected {rule['revision_count']}")

    values = " ".join((t["value"] or "") for t in analysis["terms"]).lower()
    for banned in exp.get("must_not_contain", []):
        if banned.lower() in values:
            problems.append(f"invented value '{banned}' appeared")

    return not problems, problems


def rules_only(label: dict, messages: list[Message]) -> tuple[bool, str]:
    """The whole pipeline with NO model: patterns, grounding, s.62, the
    checklist. The floor the app stands on if the model returns nothing."""
    from app.services import checklist_engine

    filled, _ = extractor.fill_gaps_with_rules([], messages)
    terms = extractor.resolve_terms(filled, messages)
    precise = extractor.anchor_relative_dates(terms, messages)
    extractor.mark_obviously_vague(terms, precise)
    result = checklist_engine.evaluate(terms)
    analysis = {
        "readiness": result.readiness.value,
        "terms": [
            {"type": t.type.value, "value": t.value, "status": t.status.value,
             "revision_state": t.revision_state.value, "revision_history": t.revision_history}
            for t in terms
        ],
    }
    ok, problems = check(label, analysis)
    return ok, "; ".join(problems) or f"{result.readiness.value}"


def run_live_checks() -> LiveReport:
    report = LiveReport()
    if not CHATS.exists():
        report.fixtures_found = False
        return report

    for path in sorted(CHATS.glob("T*.expected.json")):
        label = json.loads(path.read_text(encoding="utf-8"))
        want = label.get("parser") or {}
        scenario = label.get("scenario", "")
        try:
            parsed = parse_whatsapp_export((CHATS / label["file"]).read_bytes().decode("utf-8-sig"))
        except (OSError, ChatParseError) as exc:
            report.parser.append(CheckRow(label["id"], scenario, False, str(exc)))
            continue

        problems: list[str] = []
        if want.get("participants") is not None and parsed.participants != want["participants"]:
            problems.append(f"participants {parsed.participants}")
        if want.get("messages") is not None and len(parsed.messages) != want["messages"]:
            problems.append(f"{len(parsed.messages)} messages, expected {want['messages']}")
        if want.get("date_order") and parsed.date_order.value != want["date_order"]:
            problems.append(f"date order {parsed.date_order.value}, expected {want['date_order']}")
        attachments = sum(1 for m in parsed.messages if m.kind is MessageKind.ATTACHMENT)
        if want.get("attachments") is not None and attachments != want["attachments"]:
            problems.append(f"{attachments} attachments, expected {want['attachments']}")
        report.parser.append(
            CheckRow(label["id"], scenario, not problems,
                     "; ".join(problems) or f"{len(parsed.messages)} messages, {parsed.date_order.value}")
        )

        messages = _as_messages(parsed)
        if label.get("expected"):
            ok, detail = rules_only(label, messages)
            known = bool(label.get("known_failure")) and not ok
            # A documented limit is shown, but not counted as a regression.
            report.rules.append(CheckRow(label["id"], scenario, ok, ("known limit: " + detail) if known else detail, skipped=known))
        mask = extractor.conversation_mask(messages)
        transcript = extractor.build_transcript(messages, mask)
        leaked = pii_masker.contains_identifier(transcript)
        report.masking.append(
            CheckRow(label["id"], scenario, not leaked,
                     "identifier left in the transcript" if leaked
                     else f"{sum(mask.masked_counts.values())} identifier(s) masked")
        )

    invalid_path = CHATS / "invalid.expected.json"
    for case in json.loads(invalid_path.read_text(encoding="utf-8")) if invalid_path.exists() else []:
        path = CHATS / case["file"]
        want = case["error"]
        if not path.exists():
            report.invalid.append(CheckRow(case["id"], case["scenario"], True, "large file not generated", skipped=True))
            continue
        if want["status"] == 413 or not path.name.endswith(".txt"):
            # Enforced by the upload endpoint (size, file type), not the parser.
            report.invalid.append(CheckRow(case["id"], case["scenario"], True, f"rejected by the upload endpoint ({want['status']})", skipped=True))
            continue
        try:
            parse_whatsapp_export(path.read_bytes().decode("utf-8", errors="replace"), max_messages=5_000)
        except ChatParseError as exc:
            ok = want["message_contains"].lower() in str(exc).lower()
            report.invalid.append(CheckRow(case["id"], case["scenario"], ok, str(exc)))
        else:
            report.invalid.append(CheckRow(case["id"], case["scenario"], False, "accepted, should have been rejected"))
    return report


def last_ai_run() -> dict | None:
    """What run_eval.py wrote last, or None if it has never been run here."""
    if not LAST_RUN.exists():
        return None
    try:
        data = json.loads(LAST_RUN.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    data.setdefault("ran_at", datetime.fromtimestamp(LAST_RUN.stat().st_mtime).isoformat())
    return data
