"""Deterministic term spotting: the safety net under the language model.

The model is good at reading but not reliable: on some runs a small model
returns almost nothing (sample T04 came back with only the two parties).
These patterns find the common, high-value terms in English and Hinglish
with no model at all:

  price          "48000 all inclusive", "Do sau rupaye per piece", "180 final"
  quantity       "1000 brochures", "50 pieces"
  scope          what follows the quantity: "brochures, A4 tri-fold, glossy"
  delivery_date  "by 15 September", "parso", "kal tak", "next Monday"
  payment_due    "payment within 15 days of delivery", "payment delivery pe cash"
  advance        "20% advance", "advance 5000"

How they are used (extractor.extract): only to FILL a term type the model
returned nothing for. Every value is a substring of its message, so it still
passes the same grounding check. Patterns miss things; they never invent.

Also here: `amount_of`, which reads a money value written in digits or in
Hindi or English words, so "Do sau", "200" and "Rs. 200/-" compare equal.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.models.analysis import TermType
from app.models.conversation import Message
from app.services.chat_parser import MessageKind

# ---------------------------------------------------------------- numbers

_UNITS = {
    # English
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "fifteen": 15,
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
    "seventy": 70, "eighty": 80, "ninety": 90,
    # Hindi / Hinglish
    "ek": 1, "do": 2, "teen": 3, "char": 4, "chaar": 4, "paanch": 5, "panch": 5,
    "chhe": 6, "che": 6, "saat": 7, "aath": 8, "nau": 9, "das": 10, "bees": 20,
    "tees": 30, "chalis": 40, "pachas": 50, "pachaas": 50, "saath": 60,
    # fractions that lead a multiplier: "dedh sau" = 150, "dhai hazaar" = 2500
    "dedh": 1.5, "dhai": 2.5, "sava": 1.25, "saade": 0.5,  # saade X = X + 0.5
    "paune": -0.25,  # paune X = X - 0.25
}
_SCALES = {"sau": 100, "hundred": 100, "hazaar": 1000, "hazar": 1000, "thousand": 1000,
           "lakh": 100000, "lac": 100000, "k": 1000}

_WORD_AMOUNT = re.compile(
    r"\b((?:saade|paune|sava)\s+)?(" + "|".join(sorted((k for k in _UNITS if k not in {"saade", "paune", "sava"}), key=len, reverse=True))
    + r")\s+(" + "|".join(_SCALES) + r")\b",
    re.IGNORECASE,
)
_DIGITS = re.compile(r"(?<![\d/])(\d{1,3}(?:,\d{2,3})+|\d+(?:\.\d+)?)\s*(k|lakh|lac)?\b(?![/:]\d)", re.IGNORECASE)


def amount_of(text: str) -> float | None:
    """The first money-like amount in a value, or None.

    "Rs. 1,80,000/-" -> 180000; "Do sau rupaye" -> 200; "dedh sau" -> 150;
    "saade teen hazaar" -> 3500; "52000 final" -> 52000; "2.5 lakh" -> 250000.
    """
    lowered = text.lower()
    word = _WORD_AMOUNT.search(lowered)
    digit = _DIGITS.search(lowered)
    candidates: list[tuple[int, float]] = []
    if word:
        prefix, unit, scale = (word.group(1) or "").strip(), word.group(2), word.group(3)
        base = _UNITS[unit]
        if prefix == "saade":
            base += 0.5
        elif prefix == "paune":
            base -= 0.25
        elif prefix == "sava":
            base += 0.25
        candidates.append((word.start(), base * _SCALES[scale]))
    if digit:
        number = float(digit.group(1).replace(",", ""))
        if digit.group(2):
            number *= _SCALES[digit.group(2).lower()]
        candidates.append((digit.start(), number))
    if not candidates:
        return None
    return min(candidates)[1]


def same_value(a: str, b: str) -> bool:
    """Do two written values mean the same thing? Amounts compare by number."""
    x, y = amount_of(a), amount_of(b)
    if x is not None and y is not None:
        return abs(x - y) < 0.005
    norm = lambda s: re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", s.lower())).strip()  # noqa: E731
    return norm(a) == norm(b)


# ---------------------------------------------------------------- patterns


@dataclass(slots=True)
class RuleMention:
    type: TermType
    value: str
    source_message_ids: list[int]
    confidence: float = 0.55


_NUM = r"(?:\d{1,3}(?:,\d{2,3})+|\d+(?:\.\d+)?)"
_WORDNUM = r"(?:(?:saade|paune|sava)\s+)?(?:" + "|".join(k for k in _UNITS if k not in {"saade", "paune", "sava"}) + r")\s+(?:sau|hundred|hazaar|hazar|thousand|lakh)"

# Words that make a bare number a price.
_PRICE_CUE = r"(?:rs\.?|₹|inr|rupees?|rupaye|rupay|/-|per\s+[a-z]{2,12}|each|apiece|all\s+inclusive|inclusive|plus\s+gst|\+\s*gst|final|padega|lagega|total|rate|price|chalega|only|bas|ok|okay|done|confirmed|theek)"
_PRICE = re.compile(
    rf"(?:(?:rs\.?|₹|inr|rate|price|total|be|hoga|padega|lagega)\s*:?\s*)?(?P<amt>{_NUM}|{_WORDNUM})(?P<tail>(?:\s*(?:k|lakh|lac))?(?:\s*{_PRICE_CUE})+)"
    rf"|(?:rs\.?|₹|inr|rate|price|total|it will be|will be|becomes|hoga|padega|lagega|final|back to|do|can do|ok|okay|fine,?|yes|theek hai|haan)\s*:?\s*(?P<amt2>{_NUM}|{_WORDNUM})",
    re.IGNORECASE,
)

# Counted things. "days", "months", "%", currency and time words are not goods.
_NOT_GOODS = r"(?:days?|din|weeks?|months?|mahine|mahina|years?|hours?|hrs?|mins?|minutes?|am|pm|percent|rs|rupees?|rupaye|sau|hazaar|lakh|k|inch|feet|ft|cm|mm|am|baje|tak|se|ke|ka|ki|ko|par|pe|per|each|final|only|and|or|plus|in|at|by|on|to|for|with|the|a)"
_NOT_PRICE_AFTER = re.compile(
    r"\s*(?:%|days?\b|din\b|weeks?\b|months?\b|mahine\b|mahina\b|years?\b|hours?\b|hrs?\b|pieces?\b|pcs\b|nos\b|units?\b|am\b|pm\b|baje\b|feet\b|ft\b|inch\b)",
    re.IGNORECASE,
)
_QTY = re.compile(rf"\b(?P<n>{_NUM})\s+(?!{_NOT_GOODS}\b)(?P<noun>[a-z][a-z-]{{2,}})", re.IGNORECASE)
_ORDER_CUE = re.compile(r"\b(need|want|order|require|chahiye|bhejo|bhej do|supply|send|book|quote|make|print)\b", re.IGNORECASE)
_QTY_STOP = re.compile(
    r"^(?:for|at|this|that|please|pls|chahiye|each|per|plus|with|and|by|on|in|to|ke|ka|ki|wale|wala|"
    r"jan\w*|feb\w*|mar\w*|apr\w*|may|jun\w*|jul\w*|aug\w*|sep\w*|oct\w*|nov\w*|dec\w*|all|inclusive|only|final|ok|okay)$",
    re.IGNORECASE,
)
_MONTH_WORD = re.compile(r"^(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)", re.IGNORECASE)

_MONTHS = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
_DATE = (
    rf"(?:\d{{1,2}}(?:st|nd|rd|th)?\s+{_MONTHS}\b|{_MONTHS}\s+\d{{1,2}}(?:st|nd|rd|th)?\b|\d{{1,2}}/\d{{1,2}}(?:/\d{{2,4}})?)"
)
_RELATIVE = r"\b(?:soon|asap|jaldi|next week|this week|end of (?:the )?month|day after tomorrow|tomorrow|today|tonight|parso|parson|kal|aaj|next\s+(?:mon|tue|wed|thu|fri|sat|sun)[a-z]*|(?:mon|tues|wednes|thurs|fri|satur|sun)day)"
_DELIVERY_CUE = re.compile(r"\b(deliver\w*|dispatch\w*|ship\w*|bhej\w*|pahunch\w*|supply|ready|install\w*|complete\w*|send|by|tak|go[ -]live|live|launch\w*|handover|hand over)\b", re.IGNORECASE)
_DELIVERY = re.compile(
    rf"(?P<v>\b(?:(?:by|before|on|till|until)\s+)?{_DATE}(?:\s+tak)?|(?:(?:by|before|on|till|until)\s+)?{_RELATIVE}(?:\s+(?:tak|pakka|evening|morning|shaam|subah))?)",
    re.IGNORECASE,
)
_PAYMENT = re.compile(
    r"(?P<v>(?:(?:balance|full)\s+)?(?:payment|paisa|paise|pay|amount|bill|balance)\b[^.?!\n]{2,60})",
    re.IGNORECASE,
)
_PAYMENT_TIMING = re.compile(
    r"\b(within|after|before|on|days?|din|weeks?|months?|mahine|delivery|invoice|bill|cash|upi|neft|advance|immediately|turant|baad|pe|par|ke baad|against|credit|later|once|when)\b",
    re.IGNORECASE,
)
_ADVANCE = re.compile(
    rf"(?P<v>(?:{_NUM}\s*%?\s*(?:rs\.?\s*)?advance|advance\s+(?:of\s+)?(?:rs\.?\s*|₹\s*)?{_NUM}\s*%?))",
    re.IGNORECASE,
)


def _text_messages(messages: list[Message], skip: set[int]) -> list[Message]:
    return [m for m in messages if m.kind is MessageKind.TEXT and m.index not in skip and m.sender]


def find_mentions(messages: list[Message], skip: set[int] | None = None) -> list[RuleMention]:
    """Every pattern match, in message order. `skip`: indices never to use
    (the messages withheld as instructions to an AI)."""
    found: list[RuleMention] = []

    # --- parties: the people writing. Their names are in the export itself.
    first_by_sender: dict[str, int] = {}
    for m in _text_messages(messages, skip or set()):
        first_by_sender.setdefault(m.sender, m.index)  # type: ignore[arg-type]
    for name, index in first_by_sender.items():
        found.append(RuleMention(TermType.PARTY, name, [index], confidence=0.5))

    texts = _text_messages(messages, skip or set())
    first_index = texts[0].index if texts else -1
    previous: Message | None = None
    for m in texts:
        body = m.body

        # --- price: one per message, the first; a later "total" never
        # replaces a unit rate (it is arithmetic, not a revision)
        for match in _PRICE.finditer(body):
            amt = match.group("amt") or match.group("amt2")
            if amt is None:
                continue
            # Not a price if it is immediately a count, a duration or a date.
            after = body[match.end("amt") if match.group("amt") else match.end("amt2"):]
            if _NOT_PRICE_AFTER.match(after):
                continue
            value = match.group(0).strip(" ,.")
            amount = amount_of(value)
            if amount is None or amount < 10 or (match.group("amt2") and amount < 100):
                continue
            is_total = bool(re.search(r"\btotal\b", value, re.IGNORECASE))
            has_rate = any(
                f.type is TermType.PRICE and re.search(r"\b(per|each|apiece)\b", f.value, re.IGNORECASE)
                for f in found
            )
            if is_total and has_rate:
                continue
            found.append(RuleMention(TermType.PRICE, value, [m.index]))
            break

        # --- quantity and scope (only in a message that orders something)
        opens_with_count = m.index == first_index and re.match(rf"\s*{_NUM}\s+[a-z]", body, re.IGNORECASE)
        if _ORDER_CUE.search(body) or opens_with_count:
            for q in _QTY.finditer(body):
                if _MONTH_WORD.match(q.group("noun")) or _QTY_STOP.match(q.group("noun")):
                    continue
                # number + up to three words of what it counts: "40 office chairs"
                words: list[str] = []
                clause = re.split(r"[,.;:?!]", body[q.start("noun"):])[0]
                for w in re.findall(r"[A-Za-z][\w-]*", clause)[:3]:
                    if _QTY_STOP.match(w):
                        break
                    words.append(w)
                phrase = re.search(re.escape(q.group("n")) + r"\s+" + r"\s+".join(map(re.escape, words)), body)
                if phrase is None:
                    continue
                found.append(RuleMention(TermType.QUANTITY, phrase.group(0), [m.index]))
                scope = re.split(
                    r"[?!\n]|\.(?:\s|$)|,\s*(?=\d|delivery|payment|rate|price)|\s+(?:at|@)\s+(?:rs\.?\s*)?\d",
                    body[q.start("noun"):],
                    flags=re.IGNORECASE,
                )[0].strip(" ,.")
                if len(scope) >= 3:
                    found.append(RuleMention(TermType.SCOPE, scope, [m.index], confidence=0.45))
                break

        # --- delivery date: a cue here, or the previous message asked about it
        asked = previous is not None and previous.sender != m.sender and _DELIVERY_CUE.search(previous.body) and "?" in previous.body
        if _DELIVERY_CUE.search(body) or asked:
            d = _DELIVERY.search(body)
            if d:
                found.append(RuleMention(TermType.DELIVERY_DATE, d.group("v").strip(), [m.index]))

        # --- payment: look clause by clause, so "40% advance, balance within
        # 15 days of go-live" yields the balance terms, not the advance
        for part in re.split(r"[,;.](?:\s|$)|\n", body):
            p = _PAYMENT.search(part)
            if p and _PAYMENT_TIMING.search(p.group("v")) and not re.search(r"\badvance\b", p.group("v"), re.IGNORECASE):
                found.append(RuleMention(TermType.PAYMENT_DUE, p.group("v").strip(" ,."), [m.index]))
                break

        # --- advance
        a = _ADVANCE.search(body)
        if a:
            found.append(RuleMention(TermType.ADVANCE, a.group("v").strip(), [m.index]))

        previous = m

    return found


#: Words that make a delivery or payment term vague whatever a model says.
_OBVIOUSLY_VAGUE = re.compile(
    r"\b(soon|asap|jaldi|later|baad mein|next week|this week|as discussed|the usual|"
    r"once we check|when possible|jab ho|dekhte hain|around|approx\w*|roughly|end of (?:the )?month)\b",
    re.IGNORECASE,
)


def obviously_vague(value: str) -> bool:
    """A deterministic floor for the vagueness check: "soon", "later",
    "next week" are vague on any run, with or without the model."""
    return bool(_OBVIOUSLY_VAGUE.search(value))
