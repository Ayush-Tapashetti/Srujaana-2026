"""Scores the AI-dependent expectations of every labelled chat.

    docker compose exec server python -m tests.run_eval
    docker compose exec server python -m tests.run_eval --fresh   # bypass the cache

Runs each chat through the real pipeline (upload, extract, checklist) using
the model configured in .env, compares the result with its .expected.json
label, and prints the README results table. The table is also written to
tests/eval_results.md.

Failures are reported, never hidden: the rubric rewards honest limits and
penalises concealed ones. Cases marked known_failure are expected to fail
in the way their label describes.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

CHATS = Path(__file__).parent / "fixtures" / "chats"
OUT = Path(__file__).parent / "eval_results.md"
#: Read by the in-app evaluation page (P1-5).
OUT_JSON = Path(__file__).parent / "eval_results.json"


from app.services.eval_report import check  # noqa: E402  (shared with the evaluation page)


def main() -> int:
    if "--fresh" in sys.argv:
        os.environ["LLM_CACHE_ENABLED"] = "false"

    from fastapi.testclient import TestClient

    from app.core.config import settings
    from app.main import app

    if not (settings.groq_configured or settings.gemini_configured):
        print("No AI model configured. Set GROQ_API_KEY and GROQ_MODEL in .env first.")
        return 1

    labels = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(CHATS.glob("T*.expected.json"))]
    labels = [lab for lab in labels if lab.get("expected")]

    rows: list[str] = []
    records: list[dict] = []
    passed = dropped_total = 0

    with TestClient(app) as c:
        for lab in labels:
            raw = (CHATS / lab["file"]).read_bytes()
            up = c.post("/api/conversations", files={"file": (lab["file"], raw, "text/plain")})
            if up.status_code not in (200, 201):
                rows.append(f"| {lab['id']} | {lab['scenario']} | upload failed | | ❌ | {up.json().get('detail')} |")
                records.append({"id": lab["id"], "scenario": lab["scenario"], "expected": "", "actual": "upload failed", "passed": False, "known_failure": False, "note": str(up.json().get("detail"))})
                continue
            cid = up.json()["id"]
            res = c.post(f"/api/conversations/{cid}/extract?force=true")
            if res.status_code != 200:
                rows.append(f"| {lab['id']} | {lab['scenario']} | | error | ❌ | {res.json().get('detail')} |")
                records.append({"id": lab["id"], "scenario": lab["scenario"], "expected": "", "actual": "error", "passed": False, "known_failure": False, "note": str(res.json().get("detail"))})
                continue
            analysis = res.json()
            ok, problems = check(lab, analysis)
            dropped_total += len(analysis.get("dropped_ungrounded", []))
            known = lab.get("known_failure")
            if ok:
                passed += 1
            mark = "✅" if ok else ("⚠️ known" if known else "❌")
            note = "; ".join(problems) if problems else (lab["expected"].get("note", "") if known else "")
            expected = lab["expected"].get("overall", "")
            rows.append(
                f"| {lab['id']} | {lab['scenario']} | {expected} | {analysis['readiness']} | {mark} | {note} |"
            )
            records.append({
                "id": lab["id"], "scenario": lab["scenario"], "expected": expected,
                "actual": analysis["readiness"], "passed": ok, "known_failure": bool(known),
                "note": note, "dropped_ungrounded": len(analysis.get("dropped_ungrounded", [])),
            })
            print(f"{lab['id']}: {mark} {note}")

    table = "\n".join(
        [
            f"Model: `{settings.groq_model or settings.gemini_model}`. "
            f"{passed}/{len(labels)} passed. "
            f"{dropped_total} unsupported item(s) discarded by the grounding check across all chats.",
            "",
            "| Chat | Scenario | Expected | Actual | Pass | Notes |",
            "|---|---|---|---|---|---|",
            *rows,
        ]
    )
    OUT.write_text(table + "\n", encoding="utf-8")
    from datetime import datetime, timezone

    from app.services.llm_service import PROMPT_VERSION

    OUT_JSON.write_text(json.dumps({
        "ran_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": settings.groq_model or settings.gemini_model,
        "prompt_version": PROMPT_VERSION,
        "fresh": "--fresh" in sys.argv,
        "passed": passed,
        "total": len(labels),
        "dropped_ungrounded": dropped_total,
        "rows": records,
    }, indent=2) + "\n", encoding="utf-8")
    print("\n" + table + f"\n\nWritten to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
