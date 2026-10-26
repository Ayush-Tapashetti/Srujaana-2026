import pytest

from app.models.analysis import RevisionState, Severity, TermStatus, TermType
from app.services.checklist_engine import (
    evaluate,
    load_legal_refs,
    msme_payment_warning,
    payment_period_days,
)
from app.services.extractor import ResolvedTerm


def term(t: TermType, value: str = "x", status: TermStatus = TermStatus.CLEAR) -> ResolvedTerm:
    return ResolvedTerm(
        type=t,
        value=value,
        source_message_ids=[0],
        confidence=0.9,
        status=status,
        revision_state=(
            RevisionState.UNRESOLVED if status is TermStatus.CONFLICTED else RevisionState.NONE
        ),
    )


def complete_deal() -> list[ResolvedTerm]:
    return [
        term(TermType.PARTY, "Ravi Traders"),
        term(TermType.PARTY, "Sunrise Furniture"),
        term(TermType.SCOPE, "40 mesh-back chairs"),
        term(TermType.PRICE, "4500 per chair plus GST"),
        term(TermType.PAYMENT_DUE, "within 30 days of delivery"),
        term(TermType.DELIVERY_DATE, "15 September"),
    ]


class TestReadiness:
    def test_t1_complete_deal_is_green(self) -> None:
        result = evaluate(complete_deal())
        assert result.readiness is Severity.GREEN
        assert result.can_send

    def test_t3_missing_price_is_red_and_blocks_sending(self) -> None:
        terms = [t for t in complete_deal() if t.type is not TermType.PRICE]
        result = evaluate(terms)
        assert result.readiness is Severity.RED
        assert not result.can_send
        assert TermType.PRICE in result.missing_critical

    def test_t2_vague_delivery_is_yellow(self) -> None:
        terms = complete_deal()
        terms[-1] = term(TermType.DELIVERY_DATE, "soon", TermStatus.VAGUE)
        result = evaluate(terms)
        assert result.readiness is Severity.YELLOW
        assert result.can_send  # Yellow warns, it does not block (D8)

    def test_t5_unresolved_revision_is_red(self) -> None:
        terms = complete_deal()
        terms[3] = term(TermType.PRICE, "4200", TermStatus.CONFLICTED)
        result = evaluate(terms)
        assert result.readiness is Severity.RED
        assert any("never confirmed" in f.title for f in result.flags)

    def test_only_one_party_is_red(self) -> None:
        terms = [t for t in complete_deal() if t.value != "Sunrise Furniture"]
        assert evaluate(terms).readiness is Severity.RED

    def test_missing_advisory_terms_never_make_it_red(self) -> None:
        """Acceptance, cancellation, disputes: Yellow notes only (D7)."""
        result = evaluate(complete_deal())
        advisory = [f for f in result.flags if f.term_type is TermType.DISPUTE]
        assert advisory and advisory[0].severity is Severity.YELLOW
        assert result.readiness is Severity.GREEN

    def test_empty_chat_is_red_with_every_critical_term_missing(self) -> None:
        result = evaluate([])
        assert result.readiness is Severity.RED
        assert len(result.missing_critical) == 5


class TestLegalGrounding:
    def test_every_flag_carries_a_statute_and_section(self) -> None:
        for flag in evaluate([]).flags:
            assert flag.statute and flag.section and flag.statute_gist

    def test_missing_price_cites_s25(self) -> None:
        flags = evaluate([t for t in complete_deal() if t.type is not TermType.PRICE]).flags
        price = next(f for f in flags if f.term_type is TermType.PRICE)
        assert price.section == "s.25"

    def test_conflicted_price_cites_s62(self) -> None:
        terms = complete_deal()
        terms[3] = term(TermType.PRICE, "4200", TermStatus.CONFLICTED)
        price = next(f for f in evaluate(terms).flags if f.term_type is TermType.PRICE)
        assert price.section == "s.62"

    def test_every_flag_key_in_use_exists_in_the_reference_file(self) -> None:
        refs = load_legal_refs()
        for kind in ("missing", "vague", "conflicted"):
            for t in ("price", "payment_due", "delivery_date"):
                assert f"{kind}.{t}" in refs, f"{kind}.{t} missing from legal_refs.json"


class TestMsmeWarning:
    def test_60_days_triggers_the_45_day_warning(self) -> None:
        flag = msme_payment_warning([term(TermType.PAYMENT_DUE, "within 60 days")])
        assert flag is not None and flag.section == "s.15"

    def test_30_days_does_not(self) -> None:
        assert msme_payment_warning([term(TermType.PAYMENT_DUE, "30 days")]) is None

    @pytest.mark.parametrize(
        ("value", "days"),
        [
            ("within 60 days", 60),
            ("2 months after delivery", 60),
            ("sixty days credit", 60),
            ("do mahine baad", 60),
            ("payment in 3 weeks", 21),
            ("balance within 15 days of delivery", 15),
            ("on delivery", None),
            ("soon", None),
        ],
    )
    def test_payment_period_parsing(self, value: str, days: int | None) -> None:
        assert payment_period_days(value) == days

    def test_months_trigger_the_warning(self) -> None:
        flag = msme_payment_warning([term(TermType.PAYMENT_DUE, "2 months")])
        assert flag is not None and "60 days" in flag.title

    def test_exactly_45_days_is_allowed(self) -> None:
        assert msme_payment_warning([term(TermType.PAYMENT_DUE, "45 days")]) is None
