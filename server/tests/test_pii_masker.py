from app.services.pii_masker import contains_identifier, pseudonymise


class TestDetection:
    def test_indian_mobile_with_country_code(self) -> None:
        result = pseudonymise("call me on +91 98450 12345")
        assert "98450" not in result.text
        assert "<PHONE_1>" in result.text

    def test_bare_ten_digit_mobile(self) -> None:
        result = pseudonymise("number is 9845012345")
        assert "<PHONE_1>" in result.text

    def test_pan(self) -> None:
        result = pseudonymise("PAN ABCDE1234F for the invoice")
        assert "ABCDE1234F" not in result.text
        assert "<PAN_1>" in result.text

    def test_aadhaar(self) -> None:
        result = pseudonymise("aadhaar 1234 5678 9012")
        assert "<AADHAAR_1>" in result.text

    def test_gstin_wins_over_pan_inside_it(self) -> None:
        result = pseudonymise("GST 29ABCDE1234F1Z5 registered")
        assert "<GSTIN_1>" in result.text
        assert "<PAN_" not in result.text

    def test_email(self) -> None:
        result = pseudonymise("send to accounts@ravitraders.in please")
        assert "<EMAIL_1>" in result.text

    def test_upi_id(self) -> None:
        result = pseudonymise("pay to suresh@okaxis")
        assert "<UPI_1>" in result.text


class TestFalsePositives:
    def test_order_number_is_not_a_phone(self) -> None:
        result = pseudonymise("order 1234567890 shipped")
        assert result.mapping == {}

    def test_price_is_not_masked(self) -> None:
        result = pseudonymise("total is 202500 plus GST")
        assert result.mapping == {}

    def test_names_are_never_masked(self) -> None:
        text = "Ravi Traders and Sunrise Furniture agreed"
        assert pseudonymise(text).text == text


class TestReversibility:
    def test_restore_puts_values_back(self) -> None:
        original = "call +91 98450 12345 or mail a@b.in"
        masked = pseudonymise(original)
        assert masked.restore(masked.text) == original

    def test_same_value_reuses_one_token(self) -> None:
        result = pseudonymise("9845012345 ... again 9845012345")
        assert result.text.count("<PHONE_1>") == 2
        assert len(result.mapping) == 1

    def test_different_values_get_different_tokens(self) -> None:
        result = pseudonymise("9845012345 and 9900011122")
        assert len(result.mapping) == 2

    def test_restore_works_on_llm_output_containing_a_token(self) -> None:
        masked = pseudonymise("contact 9845012345")
        llm_said = "The buyer's contact is <PHONE_1>."
        assert masked.restore(llm_said) == "The buyer's contact is 9845012345."


class TestLeakGuard:
    def test_nothing_identifying_survives(self) -> None:
        text = (
            "Ravi on +91 98450 12345, PAN ABCDE1234F, "
            "aadhaar 1234 5678 9012, mail a@b.co.in, upi x@ybl"
        )
        assert contains_identifier(text)
        assert not contains_identifier(pseudonymise(text).text)

    def test_counts_are_reported_for_the_ui(self) -> None:
        result = pseudonymise("9845012345 and 9900011122 and a@b.in")
        assert result.masked_counts == {"PHONE": 2, "EMAIL": 1}
