"""Gap and severity rules (F3). Entirely deterministic.

The split that makes this defensible (D2): the LLM decides what is VAGUE,
because that is a judgment about language. Code decides what is MISSING and
how severe anything is, because those are rules. A rule engine can be unit
tested; a model cannot.

Colour semantics (D7), one meaning everywhere:
    RED     a critical term is missing, or revised and never agreed
    YELLOW  present but imprecise
    GREEN   clear
    overall = the worst status among the CRITICAL terms only
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.models.analysis import (
    CRITICAL_TERMS,
    RevisionState,
    Severity,
    TermStatus,
    TermType,
)
from app.services.extractor import ResolvedTerm

LEGAL_REFS_PATH = Path(__file__).parent.parent / "data" / "legal_refs.json"

#: Non-critical terms worth a Yellow note when absent, in display order.
ADVISORY_TERMS: tuple[TermType, ...] = (
    TermType.ACCEPTANCE,
    TermType.CANCELLATION,
    TermType.DISPUTE,
)

#: Order the flags appear in the UI.
_DISPLAY_ORDER: tuple[TermType, ...] = (
    TermType.PARTY,
    TermType.SCOPE,
    TermType.QUANTITY,
    TermType.PRICE,
    TermType.ADVANCE,
    TermType.PAYMENT_DUE,
    TermType.DELIVERY_DATE,
    TermType.ACCEPTANCE,
    TermType.CANCELLATION,
    TermType.DISPUTE,
)

_TERM_LABELS: dict[TermType, str] = {
    TermType.PARTY: "the other party",
    TermType.SCOPE: "what is being supplied",
    TermType.QUANTITY: "the quantity",
    TermType.PRICE: "the price",
    TermType.ADVANCE: "the advance",
    TermType.PAYMENT_DUE: "the payment date",
    TermType.DELIVERY_DATE: "the delivery date",
    TermType.ACCEPTANCE: "how the work is accepted",
    TermType.CANCELLATION: "cancellation and late payment",
    TermType.DISPUTE: "how disputes are handled",
}


@lru_cache(maxsize=1)
def load_legal_refs() -> dict[str, dict]:
    with LEGAL_REFS_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


@dataclass(slots=True)
class FlagSpec:
    term_type: TermType
    severity: Severity
    title: str
    why_it_matters: str
    statute: str
    section: str
    statute_gist: str
    suggested_question: str | None
    source_message_ids: list[int]


@dataclass(slots=True)
class ChecklistResult:
    flags: list[FlagSpec]
    readiness: Severity
    missing_critical: list[TermType]
    can_send: bool


def _ref(key: str) -> dict:
    refs = load_legal_refs()
    return refs.get(
        key,
        {
            "statute": "Indian Contract Act, 1872",
            "section": "s.10",
            "gist": "An agreement is a contract when its terms are certain "
            "and both parties have agreed to them.",
            "why_it_matters": "This term is unclear, which is where disputes start.",
            "suggested_question": None,
        },
    )


def _flag(
    term_type: TermType,
    severity: Severity,
    key: str,
    title: str,
    source_message_ids: list[int],
    why_override: str | None = None,
    question_override: str | None = None,
) -> FlagSpec:
    ref = _ref(key)
    return FlagSpec(
        term_type=term_type,
        severity=severity,
        title=title,
        why_it_matters=why_override or ref["why_it_matters"],
        statute=ref["statute"],
        section=ref["section"],
        statute_gist=ref["gist"],
        suggested_question=question_override or ref.get("suggested_question"),
        source_message_ids=source_message_ids,
    )


def evaluate(terms: list[ResolvedTerm]) -> ChecklistResult:
    """Produce the flag list and the overall readiness badge."""
    by_type: dict[TermType, list[ResolvedTerm]] = {}
    for term in terms:
        by_type.setdefault(term.type, []).append(term)

    flags: list[FlagSpec] = []
    missing_critical: list[TermType] = []

    for term_type in _DISPLAY_ORDER:
        found = by_type.get(term_type, [])
        label = _TERM_LABELS[term_type]
        is_critical = term_type in CRITICAL_TERMS

        # A chat has two sides, so one named party is still a gap.
        if term_type is TermType.PARTY and len(found) == 1:
            flags.append(
                _flag(
                    term_type,
                    Severity.RED,
                    "missing.party",
                    "Only one party is identifiable",
                    found[0].source_message_ids,
                )
            )
            missing_critical.append(term_type)
            continue

        if not found:
            if is_critical:
                missing_critical.append(term_type)
                flags.append(
                    _flag(
                        term_type,
                        Severity.RED,
                        f"missing.{term_type.value}",
                        f"No agreement on {label}",
                        [],
                    )
                )
            elif term_type in ADVISORY_TERMS:
                flags.append(
                    _flag(
                        term_type,
                        Severity.YELLOW,
                        f"missing.{term_type.value}",
                        f"Nothing agreed about {label}",
                        [],
                    )
                )
            continue

        for term in found:
            if (
                term.status is TermStatus.CONFLICTED
                and term.sarcastic_reply_index is not None
            ):
                # The other side DID reply, but the reply reads as sarcasm,
                # so it is not counted as agreement. Saying "they never
                # replied" here would be untrue.
                flags.append(
                    _flag(
                        term_type,
                        Severity.RED,
                        f"conflicted.{term_type.value}",
                        f"The reply to the change in {label} may be sarcasm, not agreement",
                        sorted({*term.source_message_ids, term.sarcastic_reply_index}),
                        why_override=(
                            f"A later message proposed a change to {label} "
                            f"({term.value}). The reply reads as sarcasm or a "
                            "refusal (for example an eye-roll emoji or an "
                            "exaggerated extra demand), so it was not counted "
                            "as agreement. Each side may now believe something "
                            "different."
                        ),
                        question_override=(
                            "To be sure we are on the same page, can you say "
                            "plainly whether you accept this, yes or no?"
                        ),
                    )
                )
            elif term.status is TermStatus.CONFLICTED:
                flags.append(
                    _flag(
                        term_type,
                        Severity.RED,
                        f"conflicted.{term_type.value}",
                        f"{label.capitalize()} was changed and never confirmed",
                        term.source_message_ids,
                        why_override=(
                            f"A later message proposed a change to {label} "
                            f"({term.value}), and the other side never "
                            "replied to it. Each side may now believe "
                            "something different."
                        ),
                    )
                )
            elif term.status is TermStatus.VAGUE:
                flags.append(
                    _flag(
                        term_type,
                        Severity.YELLOW,
                        f"vague.{term_type.value}",
                        f"{label.capitalize()} is not precise",
                        term.source_message_ids,
                    )
                )

    readiness = _readiness(by_type, missing_critical)
    return ChecklistResult(
        flags=flags,
        readiness=readiness,
        missing_critical=missing_critical,
        can_send=readiness is not Severity.RED,
    )


def _readiness(
    by_type: dict[TermType, list[ResolvedTerm]],
    missing_critical: list[TermType],
) -> Severity:
    """Overall = the worst status among critical terms only (D7)."""
    if missing_critical:
        return Severity.RED

    critical_terms = [
        term
        for term_type, group in by_type.items()
        if term_type in CRITICAL_TERMS
        for term in group
    ]
    if any(t.status is TermStatus.CONFLICTED for t in critical_terms):
        return Severity.RED
    if any(t.status is TermStatus.VAGUE for t in critical_terms):
        return Severity.YELLOW
    return Severity.GREEN


_NUMBER_WORDS = {
    "one": 1, "ek": 1, "a": 1, "an": 1, "two": 2, "do": 2, "three": 3, "teen": 3,
    "four": 4, "char": 4, "chaar": 4, "five": 5, "paanch": 5, "six": 6, "chhe": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "fifteen": 15, "twenty": 20,
    "thirty": 30, "forty": 40, "forty-five": 45, "fortyfive": 45, "fifty": 50,
    "sixty": 60, "seventy": 70, "seventy-five": 75, "eighty": 80, "ninety": 90,
    "hundred": 100, "dedh": 1.5,
}
_UNIT_DAYS = {
    "day": 1, "days": 1, "din": 1, "dino": 1,
    "week": 7, "weeks": 7, "hafta": 7, "hafte": 7,
    "month": 30, "months": 30, "mahina": 30, "mahine": 30, "mahino": 30,
}
_PERIOD = re.compile(
    r"(\d{1,3}(?:\.\d)?|[a-z]+(?:-[a-z]+)?)\s*(days?|din|dino|weeks?|hafta|hafte|months?|mahin[aeo])\b"
)


def payment_period_days(value: str) -> int | None:
    """Longest payment period stated in a term, in days.

    "within 60 days" -> 60, "2 months" -> 60, "sixty days" -> 60,
    "do mahine baad" -> 60. A month counts as 30 days, the conservative
    reading for a 45-day cap. Returns None when no period is stated
    ("on delivery", "soon"), which is never flagged.
    """
    best: float | None = None
    for amount, unit in _PERIOD.findall(value.lower()):
        number = float(amount) if amount[0].isdigit() else _NUMBER_WORDS.get(amount)
        if number is None:
            continue
        days = number * _UNIT_DAYS[unit]
        best = days if best is None else max(best, days)
    return None if best is None else int(round(best))


#: The limit in MSMED Act s.15, where no shorter period is agreed.
MSME_MAX_DAYS = 45


def msme_payment_warning(terms: list[ResolvedTerm]) -> FlagSpec | None:
    """P1-2. Flags a payment term beyond the statutory 45-day maximum.

    Shown only once the owner has said the supplier is a registered micro or
    small enterprise, because the limit applies to those suppliers. The
    statutory cap overrides a longer period agreed in a contract, which is
    the part almost no small supplier knows. Advisory: it never changes
    readiness, because whether the supplier is registered is not in the chat.
    """
    for term in terms:
        if term.type is not TermType.PAYMENT_DUE or not term.value:
            continue
        days = payment_period_days(term.value)
        if days is not None and days > MSME_MAX_DAYS:
            return _flag(
                TermType.PAYMENT_DUE,
                Severity.YELLOW,
                "msme.payment_term_exceeds_45_days",
                f"Payment term ({days} days) is longer than the statutory maximum",
                term.source_message_ids,
            )
    return None
