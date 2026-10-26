"""WhatsApp .txt export parser (F1).

Pure function: text in, typed messages out. No database, no LLM, no I/O.
That is what makes it exhaustively unit-testable, which is where the
validation marks come from.

Two decisions worth knowing before reading the code:

1. Date order is resolved by scanning the WHOLE file before parsing any line.
   `03/04/24` is unresolvable on its own, but one `25/01/24` anywhere settles
   the format for every line. Guessing per-line would silently reverse the
   timeline, and the timeline is what the revision logic depends on.

2. Messages are addressed by `index` (0-based position in the conversation),
   not by database id. `source_message_ids` everywhere in this codebase means
   these indices: they are small, stable, and can be shown to the LLM in the
   prompt so it can cite them back.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class DateOrder(str, Enum):
    DAY_FIRST = "day_first"
    MONTH_FIRST = "month_first"
    AMBIGUOUS = "ambiguous"


class MessageKind(str, Enum):
    TEXT = "text"
    ATTACHMENT = "attachment"  # D1: present in the export, never analysed
    SYSTEM = "system"
    DELETED = "deleted"


@dataclass(slots=True)
class ParsedMessage:
    index: int
    timestamp: datetime
    sender: str | None
    body: str
    kind: MessageKind
    raw: str


@dataclass(slots=True)
class ParseResult:
    messages: list[ParsedMessage]
    date_order: DateOrder
    participants: list[str]
    unparsed_lines: int
    attachment_indices: list[int] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class ChatParseError(ValueError):
    """The input is not a usable WhatsApp export. Surfaced to the user as 400."""


# Newer exports put a narrow or non-breaking space before am/pm.
_SP = r"[\s  ]"

_TIME = (
    rf"(?P<hh>\d{{1,2}}):(?P<mi>\d{{2}})(?::(?P<ss>\d{{2}}))?"
    rf"(?:{_SP}*(?P<ap>[ap]\.?m\.?))?"
)
_DATE = r"(?P<a>\d{1,2})[/.-](?P<b>\d{1,2})[/.-](?P<y>\d{2,4})"

ANDROID_RE = re.compile(
    rf"^{_DATE},?{_SP}+{_TIME}{_SP}*-{_SP}*(?P<rest>.*)$", re.IGNORECASE
)
IOS_RE = re.compile(rf"^\[{_DATE},?{_SP}+{_TIME}\]{_SP}*(?P<rest>.*)$", re.IGNORECASE)

_ATTACHMENT_MARKERS = (
    "<media omitted>",
    "image omitted",
    "video omitted",
    "audio omitted",
    "sticker omitted",
    "document omitted",
    "gif omitted",
    "contact card omitted",
    "(file attached)",
)
_DELETED_MARKERS = (
    "this message was deleted",
    "you deleted this message",
)
_SYSTEM_MARKERS = (
    "messages and calls are end-to-end encrypted",
    "created group",
    "added you",
    "changed the subject",
    "changed this group's icon",
    "joined using this group's invite link",
    "changed their phone number",
    "your security code with",
)

MAX_SENDER_LEN = 80


def _header(line: str) -> re.Match[str] | None:
    return IOS_RE.match(line) or ANDROID_RE.match(line)


def _detect_date_order(lines: list[str]) -> tuple[DateOrder, list[str]]:
    """A value above 12 in either slot settles the format for the whole file."""
    warnings: list[str] = []
    first_max = second_max = 0

    for line in lines:
        m = _header(line)
        if m is None:
            continue
        first_max = max(first_max, int(m.group("a")))
        second_max = max(second_max, int(m.group("b")))

    if first_max > 12 and second_max <= 12:
        return DateOrder.DAY_FIRST, warnings
    if second_max > 12 and first_max <= 12:
        return DateOrder.MONTH_FIRST, warnings
    if first_max > 12 and second_max > 12:
        raise ChatParseError(
            "The dates in this file are inconsistent, so it cannot be read "
            "as a WhatsApp export."
        )

    warnings.append(
        "Every date in this chat fits both DD/MM and MM/DD. We assumed DD/MM "
        "(the Indian default). Check the message order before relying on it."
    )
    return DateOrder.AMBIGUOUS, warnings


def _build_timestamp(m: re.Match[str], order: DateOrder) -> datetime:
    a, b = int(m.group("a")), int(m.group("b"))
    day, month = (b, a) if order is DateOrder.MONTH_FIRST else (a, b)

    year = int(m.group("y"))
    if year < 100:
        year += 2000

    hour = int(m.group("hh"))
    minute = int(m.group("mi"))
    second = int(m.group("ss") or 0)

    marker = (m.group("ap") or "").replace(".", "").lower()
    if marker == "pm" and hour != 12:
        hour += 12
    elif marker == "am" and hour == 12:
        hour = 0

    try:
        return datetime(year, month, day, hour, minute, second)
    except ValueError as exc:  # 31/02, hour 25, and similar
        raise ChatParseError(f"Unreadable date or time in the export: {exc}") from exc


def _split_sender(rest: str) -> tuple[str | None, str]:
    """System lines carry no 'Sender: ' prefix, so sender is None for them."""
    head, separator, tail = rest.partition(": ")
    if not separator or "\n" in head or len(head) > MAX_SENDER_LEN:
        return None, rest.strip()
    return head.strip(), tail.strip()


def _classify(sender: str | None, body: str) -> MessageKind:
    low = body.lower().strip()
    if sender is None or any(marker in low for marker in _SYSTEM_MARKERS):
        return MessageKind.SYSTEM
    if any(marker in low for marker in _DELETED_MARKERS):
        return MessageKind.DELETED
    if any(marker in low for marker in _ATTACHMENT_MARKERS):
        return MessageKind.ATTACHMENT
    return MessageKind.TEXT


def parse_whatsapp_export(
    raw_text: str, *, max_messages: int = 5_000
) -> ParseResult:
    """Parse an export into ordered messages. Raises ChatParseError on bad input."""
    text = raw_text.replace("\r\n", "\n").lstrip("﻿")
    lines = text.split("\n")

    if not text.strip():
        raise ChatParseError("This file is empty.")

    if not any(_header(line) for line in lines):
        raise ChatParseError(
            "No WhatsApp messages found in this file. In WhatsApp, open the "
            "chat, then More options -> Export chat -> Without media, and "
            "upload the .txt file it produces."
        )

    order, warnings = _detect_date_order(lines)

    messages: list[ParsedMessage] = []
    buffer: list[str] = []
    current: re.Match[str] | None = None
    unparsed = 0

    def flush() -> None:
        nonlocal current, buffer
        if current is None:
            return
        rest = "\n".join([current.group("rest"), *buffer]).strip()
        sender, body = _split_sender(rest)
        messages.append(
            ParsedMessage(
                index=len(messages),
                timestamp=_build_timestamp(current, order),
                sender=sender,
                body=body,
                kind=_classify(sender, body),
                raw=rest,
            )
        )
        current, buffer = None, []

    for line in lines:
        header = _header(line)
        if header is not None:
            flush()
            current = header
        elif current is not None:
            buffer.append(line)  # continuation of a multi-line message
        elif line.strip():
            unparsed += 1
    flush()

    if len(messages) > max_messages:
        raise ChatParseError(
            f"This chat has {len(messages):,} messages and the limit is "
            f"{max_messages:,}. Export a shorter date range."
        )

    participants = sorted(
        {
            m.sender
            for m in messages
            if m.sender and m.kind is not MessageKind.SYSTEM
        }
    )

    attachment_indices = [
        m.index for m in messages if m.kind is MessageKind.ATTACHMENT
    ]

    if len(participants) > 2:
        warnings.append(
            f"This chat has {len(participants)} participants. We cannot "
            "reliably tell which two are the contracting parties, so check "
            "the parties yourself."
        )
    if attachment_indices:
        warnings.append(
            f"{len(attachment_indices)} voice note(s) or image(s) are in this "
            "chat. We do not analyse them, so add any terms they carry yourself."
        )

    return ParseResult(
        messages=messages,
        date_order=order,
        participants=participants,
        unparsed_lines=unparsed,
        attachment_indices=attachment_indices,
        warnings=warnings,
    )
