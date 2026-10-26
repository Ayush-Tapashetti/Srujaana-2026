"""Reversible identifier pseudonymisation, run before any LLM call (F1, D6).

Why pseudonymise rather than delete:

The LLM must never see a phone number, PAN or Aadhaar. But F3 flags a party
as Yellow when there is "a name only, no business identity or contact", and
F4 puts the real contact details in the finished agreement. Deleting the
value would make that flag unclearable and strip the agreement.

So each identifier becomes a stable token (`<PHONE_1>`), the mapping stays on
our server, and real values are substituted back into the model's output.
Identical values reuse the same token, so the model can still tell that two
messages mention the same number.

Names are deliberately NOT masked: they are the one thing F2 must extract,
and they appear in the agreement either way.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Order matters: the more specific patterns run first so that, for example,
# a GSTIN is not partly consumed by the PAN pattern inside it.
_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("GSTIN", re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d]\b")),
    ("PAN", re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")),
    ("AADHAAR", re.compile(r"(?<!\d)\d{4}[\s-]?\d{4}[\s-]?\d{4}(?!\d)")),
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]{2,}\b")),
    (
        "UPI",
        re.compile(
            r"\b[\w.-]{3,}@(?:okaxis|okhdfcbank|okicici|oksbi|ybl|paytm|upi|ibl|apl)\b",
            re.IGNORECASE,
        ),
    ),
    ("PHONE", re.compile(r"(?<![\d@])(?:\+91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?![\d])")),
]


@dataclass(slots=True)
class Pseudonymised:
    text: str
    mapping: dict[str, str] = field(default_factory=dict)  # token -> original

    @property
    def masked_counts(self) -> dict[str, int]:
        """For the UI note: {'PHONE': 2, 'EMAIL': 1}."""
        counts: dict[str, int] = {}
        for token in self.mapping:
            label = token.strip("<>").rsplit("_", 1)[0]
            counts[label] = counts.get(label, 0) + 1
        return counts

    def restore(self, text: str) -> str:
        """Put the real values back into text that came out of the LLM."""
        for token, original in self.mapping.items():
            text = text.replace(token, original)
        return text


def pseudonymise(text: str) -> Pseudonymised:
    mapping: dict[str, str] = {}
    reverse: dict[str, str] = {}  # original -> token, so repeats stay stable
    counters: dict[str, int] = {}

    def replace(label: str, match: re.Match[str]) -> str:
        value = match.group(0)
        if value in reverse:
            return reverse[value]
        counters[label] = counters.get(label, 0) + 1
        token = f"<{label}_{counters[label]}>"
        mapping[token] = value
        reverse[value] = token
        return token

    for label, pattern in _PATTERNS:
        text = pattern.sub(lambda m, lb=label: replace(lb, m), text)

    return Pseudonymised(text=text, mapping=mapping)


#: Joins messages for one masking pass. A symbol no pattern can match, and
#: that never appears in a WhatsApp export.
_SEPARATOR = "\n␞\n"


def pseudonymise_many(texts: list[str]) -> tuple[list[str], Pseudonymised]:
    """Mask several texts with ONE shared token map.

    The same phone number gets the same token in every message, so the
    model can still tell that two messages mention the same number.
    """
    shared = pseudonymise(_SEPARATOR.join(texts))
    parts = shared.text.split(_SEPARATOR)
    if len(parts) != len(texts):  # defensive: never mis-align messages
        raise ValueError("masking changed the number of messages")
    return parts, shared


def mask_with(result: Pseudonymised, text: str) -> str:
    """Apply an existing token map to new text (original -> token)."""
    for token, original in sorted(result.mapping.items(), key=lambda kv: -len(kv[1])):
        text = text.replace(original, token)
    return text


def contains_identifier(text: str) -> bool:
    """Test helper: asserts nothing leaked into the prompt."""
    return any(pattern.search(text) for _, pattern in _PATTERNS)
