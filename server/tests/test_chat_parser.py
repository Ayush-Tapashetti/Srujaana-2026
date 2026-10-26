import pytest

from app.services.chat_parser import (
    ChatParseError,
    DateOrder,
    MessageKind,
    parse_whatsapp_export,
)

ANDROID = """12/08/24, 10:14 pm - Ravi Traders: Need 40 chairs
12/08/24, 10:16 pm - Sunrise Furniture: 4500 each, 3 weeks
13/08/24, 9:02 am - Ravi Traders: Make it 45
and send the invoice by email
13/08/24, 9:05 am - Sunrise Furniture: <Media omitted>
"""

IOS = """[12/08/2024, 10:14:03 PM] Ravi Traders: Need 40 chairs
[12/08/2024, 10:16:11 PM] Sunrise Furniture: 4500 each
"""

TWENTY_FOUR_HOUR = """12/08/2024, 22:14 - Ravi Traders: Need 40 chairs
12/08/2024, 22:16 - Sunrise Furniture: Fine
"""


class TestFormats:
    def test_parses_android_export(self) -> None:
        result = parse_whatsapp_export(ANDROID)
        assert len(result.messages) == 4
        assert result.participants == ["Ravi Traders", "Sunrise Furniture"]

    def test_parses_ios_export(self) -> None:
        result = parse_whatsapp_export(IOS)
        assert len(result.messages) == 2
        assert result.messages[0].timestamp.second == 3

    def test_parses_24_hour_time(self) -> None:
        result = parse_whatsapp_export(TWENTY_FOUR_HOUR)
        assert result.messages[0].timestamp.hour == 22

    def test_12_hour_pm_converts(self) -> None:
        result = parse_whatsapp_export(ANDROID)
        assert result.messages[0].timestamp.hour == 22

    def test_midnight_12am_is_hour_zero(self) -> None:
        result = parse_whatsapp_export("12/08/24, 12:30 am - A: hi\n")
        assert result.messages[0].timestamp.hour == 0

    def test_noon_12pm_stays_twelve(self) -> None:
        result = parse_whatsapp_export("12/08/24, 12:30 pm - A: hi\n")
        assert result.messages[0].timestamp.hour == 12

    def test_narrow_space_before_meridiem(self) -> None:
        result = parse_whatsapp_export("12/08/24, 10:14 pm - A: hi\n")
        assert result.messages[0].timestamp.hour == 22

    def test_bom_is_stripped(self) -> None:
        result = parse_whatsapp_export("﻿12/08/24, 10:14 am - A: hi\n")
        assert len(result.messages) == 1

    def test_crlf_line_endings(self) -> None:
        result = parse_whatsapp_export("12/08/24, 10:14 am - A: hi\r\n")
        assert len(result.messages) == 1


class TestStructure:
    def test_multiline_message_is_joined(self) -> None:
        result = parse_whatsapp_export(ANDROID)
        assert "send the invoice" in result.messages[2].body
        assert len(result.messages) == 4  # not split into a fifth

    def test_indices_are_sequential(self) -> None:
        result = parse_whatsapp_export(ANDROID)
        assert [m.index for m in result.messages] == [0, 1, 2, 3]

    def test_sender_and_body_split(self) -> None:
        result = parse_whatsapp_export(ANDROID)
        assert result.messages[0].sender == "Ravi Traders"
        assert result.messages[0].body == "Need 40 chairs"

    def test_colon_in_body_does_not_break_sender(self) -> None:
        result = parse_whatsapp_export(
            "12/08/24, 10:14 am - A: deadline: next Friday\n"
        )
        assert result.messages[0].sender == "A"
        assert result.messages[0].body == "deadline: next Friday"


class TestClassification:
    def test_attachment_is_flagged(self) -> None:
        result = parse_whatsapp_export(ANDROID)
        assert result.messages[3].kind is MessageKind.ATTACHMENT
        assert result.attachment_indices == [3]

    def test_attachment_produces_a_warning(self) -> None:
        result = parse_whatsapp_export(ANDROID)
        assert any("voice note" in w for w in result.warnings)

    def test_system_line_has_no_sender(self) -> None:
        text = (
            "12/08/24, 10:00 am - Messages and calls are end-to-end encrypted.\n"
            "12/08/24, 10:14 am - A: hi\n"
        )
        result = parse_whatsapp_export(text)
        assert result.messages[0].kind is MessageKind.SYSTEM
        assert result.participants == ["A"]

    def test_deleted_message(self) -> None:
        result = parse_whatsapp_export(
            "12/08/24, 10:14 am - A: This message was deleted\n"
        )
        assert result.messages[0].kind is MessageKind.DELETED


class TestDateOrder:
    def test_day_first_detected_from_high_day_value(self) -> None:
        result = parse_whatsapp_export("25/01/24, 10:00 - A: hi\n")
        assert result.date_order is DateOrder.DAY_FIRST
        assert result.messages[0].timestamp.month == 1
        assert result.messages[0].timestamp.day == 25

    def test_month_first_detected(self) -> None:
        result = parse_whatsapp_export("01/25/24, 10:00 - A: hi\n")
        assert result.date_order is DateOrder.MONTH_FIRST
        assert result.messages[0].timestamp.day == 25

    def test_one_unambiguous_line_settles_the_whole_file(self) -> None:
        text = "03/04/24, 10:00 - A: hi\n25/04/24, 10:00 - A: later\n"
        result = parse_whatsapp_export(text)
        assert result.date_order is DateOrder.DAY_FIRST
        assert result.messages[0].timestamp.month == 4

    def test_ambiguous_dates_warn_rather_than_guess_silently(self) -> None:
        result = parse_whatsapp_export("03/04/24, 10:00 - A: hi\n")
        assert result.date_order is DateOrder.AMBIGUOUS
        assert result.warnings


class TestInvalidInput:
    def test_empty_file_rejected(self) -> None:
        with pytest.raises(ChatParseError, match="empty"):
            parse_whatsapp_export("   \n  \n")

    def test_junk_file_rejected(self) -> None:
        with pytest.raises(ChatParseError, match="No WhatsApp messages"):
            parse_whatsapp_export("just a text file\nwith no chat in it\n")

    def test_impossible_date_rejected(self) -> None:
        with pytest.raises(ChatParseError):
            parse_whatsapp_export("31/02/24, 10:00 - A: hi\n")

    def test_too_many_messages_rejected(self) -> None:
        text = "".join(f"12/08/24, 10:14 am - A: m{i}\n" for i in range(12))
        with pytest.raises(ChatParseError, match="limit"):
            parse_whatsapp_export(text, max_messages=10)


class TestGroupChat:
    def test_three_participants_warns(self) -> None:
        text = (
            "12/08/24, 10:00 am - A: hi\n"
            "12/08/24, 10:01 am - B: hello\n"
            "12/08/24, 10:02 am - C: hey\n"
        )
        result = parse_whatsapp_export(text)
        assert len(result.participants) == 3
        assert any("participants" in w for w in result.warnings)
