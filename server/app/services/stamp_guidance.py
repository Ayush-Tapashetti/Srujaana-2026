"""Stamp duty guidance (F7, D5). A data lookup, never a calculation.

The legal effect is the part most sources get wrong, so it is stated
precisely: an unstamped agreement is generally NOT void, but it may be
inadmissible in evidence until the duty and any penalty are paid, and the
defect is curable.

Every rate in the data file is null on purpose. A rate appears only after a
team member reads it off the state's own schedule and records the date. A
guessed number would cost more on domain correctness than the coverage is
worth.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

STAMP_DATA_PATH = Path(__file__).parent.parent / "data" / "stamp_duty.json"


@lru_cache(maxsize=1)
def _data() -> dict:
    with STAMP_DATA_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


@dataclass(slots=True)
class StampGuidance:
    supported: bool
    state_code: str
    state_name: str | None
    state_act: str | None
    authority: str | None
    source_url: str | None
    last_verified: str | None
    duty_rate: str | None
    rate_note: str | None
    estamping_available: bool
    headline: str
    plain_language: str
    points: list[dict]
    checklist: list[str]
    message: str | None = None


def supported_states() -> list[dict[str, str]]:
    return [
        {"code": code, "name": entry["name"]}
        for code, entry in sorted(_data()["states"].items())
    ]


def guidance_for(state_code: str | None) -> StampGuidance:
    data = _data()
    general = data["general_effect"]
    code = (state_code or "").strip().upper()
    state = data["states"].get(code)

    if state is None:
        return StampGuidance(
            supported=False,
            state_code=code,
            state_name=None,
            state_act=None,
            authority=None,
            source_url=None,
            last_verified=None,
            duty_rate=None,
            rate_note=None,
            estamping_available=False,
            headline=general["headline"],
            plain_language=general["plain_language"],
            points=general["points"],
            checklist=general["checklist"],
            message=data["unsupported_state_message"],
        )

    return StampGuidance(
        supported=True,
        state_code=code,
        state_name=state["name"],
        state_act=state["state_act"],
        authority=state["authority"],
        source_url=state["source_url"],
        last_verified=state["last_verified"],
        duty_rate=state["duty_rate"],
        rate_note=state["rate_note"],
        estamping_available=state["estamping_available"],
        headline=general["headline"],
        plain_language=general["plain_language"],
        points=general["points"],
        checklist=general["checklist"],
    )
