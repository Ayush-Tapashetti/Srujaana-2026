"""Sarcasm guard for replies that would otherwise count as assent.

Why this exists. The settlement rule (extractor._accepts) treats a reply that
starts with "ok", "sure", "haan" and so on as acceptance of a revised term.
That is right for "ok sir" and wrong for:

    "ok sure, and I'll deliver them on a golden chariot also 🙄"

A language model does not reliably catch this, and neither does a word list
of assent. So this module decides, in code (like every other judgment in
this app that matters), whether a reply READS as sarcasm. When it does, the
reply is not counted as agreement: the term stays unconfirmed (Red), with a
flag that says why, instead of quietly turning Green.

How it decides. Signals are weighted, and a reply is called sarcastic when
the weights reach THRESHOLD:

    strong (2)   an eye-roll style emoji, a trailing "/s", or a stock
                 sarcastic phrase ("yeah right", "dream on", "mazak hai kya")
    medium (1)   an exaggerated, impossible extra demand ("golden chariot",
                 "on the moon"), assent followed by "and I'll ... also",
                 "while you're at it", "wow", "haan haan", laughter, a
                 trailing ellipsis after assent, assent in quotation marks

One strong signal is enough. Two medium signals are enough. One medium
signal alone is not: "ok, and I'll send the invoice tomorrow too" is a
normal reply and must stay assent.

Honest limits. This is a pattern guard, not understanding. Sarcasm with no
emoji, no stock phrase and no exaggeration ("great, just great") passes as
assent, and a genuine reply that happens to use an eye-roll emoji is held
for confirmation. Holding a genuine "ok" for confirmation costs one
message; accepting a sarcastic one can cost a deal, so the guard leans that
way on purpose. Pure Python, no imports from the app, so it can be tested
alone.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: Weight at or above which a reply is treated as sarcastic.
THRESHOLD = 2

STRONG = 2
MEDIUM = 1

# Emoji that, on a reply to a proposal, almost always mean "no / as if".
_EYE_ROLL_EMOJI = (
    "🙄", "😒", "🙃", "😏", "😑", "🤨", "🤡", "🤦", "😤", "😮‍💨",
)

_STRONG_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (label, re.compile(pattern, re.IGNORECASE))
    for label, pattern in (
        ("trailing /s", r"(?:^|\s)/s\s*$"),
        ("stock sarcastic phrase", r"\b(?:yeah|yea|yep|oh)\s+(?:right|sure)\b"),
        ("stock sarcastic phrase", r"\bas if\b"),
        ("stock sarcastic phrase", r"\b(?:dream on|keep dreaming|in your dreams)\b"),
        ("stock sarcastic phrase", r"\bgood luck with that\b"),
        ("stock sarcastic phrase", r"\bwhen pigs fly\b|\bnot in this lifetime\b|\bover my dead body\b"),
        ("stock sarcastic phrase", r"\b(?:very|real|so) funny\b|\bnice joke\b|\bhilarious\b"),
        ("stock sarcastic phrase", r"\b(?:you must be|are you|you're|you are) (?:joking|kidding)\b|\bis this a joke\b"),
        ("stock sarcastic phrase", r"\bwhat a joke\b|\bjoke of the (?:day|year)\b"),
        # Hindi / Hinglish
        ("stock sarcastic phrase", r"\bmaza?a?k\b.{0,12}\b(?:hai|kar|samajh|bana)\b|\bmazak (?:chal|kar)\b"),
        ("stock sarcastic phrase", r"\bsapne (?:me|mein|dekho)\b|\bsapne dekh\b"),
        ("stock sarcastic phrase", r"\bwah+\s+wah+\b|\bwaah+\s+waah+\b"),
        ("stock sarcastic phrase", r"\bhaan\s+haan\s+(?:bilkul|zaroor|kyun nahi)\b"),
    )
]

# Impossible or comic extras: nobody means these literally.
_EXAGGERATION = re.compile(
    r"\b(?:golden|gold(?:en)? (?:chariot|plated)|chariot|on the moon|from the moon|helicopter|"
    r"private jet|red carpet|silver platter|on a platter|gift[- ]?wrapped|unicorn|"
    r"magic wand|genie|santa|fairy|rainbow|your (?:highness|majesty)|maharaj|"
    r"sone ka|chaand|chand pe|udake|ud ke)\b",
    re.IGNORECASE,
)

_ASSENT_LEAD = re.compile(
    r"^\W*(?:ok(?:ay|k)?|sure|fine|yes|yeah|yep|haan|han|ha|theek(?: hai)?|thik(?: hai)?|"
    r"done|agreed|alright|absolutely|of course|bilkul|zaroor)\b",
    re.IGNORECASE,
)

# "ok sure, and I'll deliver ... also": assent plus an unasked-for extra.
_AND_ILL_ALSO = re.compile(
    r"\band\b.{0,30}\b(?:i'll|i will|i shall|we'll|we will|main|hum)\b.{0,80}\b(?:also|too|as well|bhi)\b",
    re.IGNORECASE,
)

_MEDIUM_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (label, re.compile(pattern, re.IGNORECASE))
    for label, pattern in (
        ("'while you're at it' style extra", r"\bwhile you(?:'re| are) at it\b|\bmight as well\b|\banything else\b|\bwhat next\b|\bwhy not also\b"),
        ("'wow' reaction", r"\b(?:oh+\s+)?wow+\b|\bwaah+\b|\bwah+\b(?!\s+wah)"),
        ("doubled assent", r"\b(?:haan haan|han han|sure sure|yes yes|ok ok|okk okk|theek hai theek hai)\b"),
        ("laughter", r"\b(?:lol|lmao|rofl|haha+|hehe+)\b|😂|🤣"),
        ("assent in quotation marks", r"[\"“”']\s*(?:ok(?:ay)?|sure|fine|agreed|done)\s*[\"“”']"),
    )
]

_TRAILING_ELLIPSIS = re.compile(r"(?:\.{3,}|…)\s*\W*$")


@dataclass(frozen=True, slots=True)
class SarcasmVerdict:
    sarcastic: bool
    score: int
    signals: tuple[str, ...]


def assess(reply: str) -> SarcasmVerdict:
    """Score a reply. `signals` names what was found, for logs and tests."""
    text = reply.strip()
    if not text:
        return SarcasmVerdict(False, 0, ())

    score = 0
    signals: list[str] = []

    def hit(weight: int, label: str) -> None:
        nonlocal score
        if label not in signals:
            score += weight
            signals.append(label)

    if any(e in text for e in _EYE_ROLL_EMOJI):
        hit(STRONG, "eye-roll emoji")

    for label, pattern in _STRONG_PATTERNS:
        if pattern.search(text):
            hit(STRONG, label)

    if _EXAGGERATION.search(text):
        hit(MEDIUM, "exaggerated extra demand")

    leads_with_assent = bool(_ASSENT_LEAD.search(text))

    if leads_with_assent and _AND_ILL_ALSO.search(text):
        hit(MEDIUM, "assent plus an extra duty")

    if leads_with_assent and _TRAILING_ELLIPSIS.search(text):
        hit(MEDIUM, "assent trailing off")

    for label, pattern in _MEDIUM_PATTERNS:
        if pattern.search(text):
            hit(MEDIUM, label)

    return SarcasmVerdict(score >= THRESHOLD, score, tuple(signals))


def looks_sarcastic(reply: str) -> bool:
    """True when the reply should NOT be counted as agreement."""
    return assess(reply).sarcastic
