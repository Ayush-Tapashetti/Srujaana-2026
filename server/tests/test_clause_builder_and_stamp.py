from app.models.analysis import RevisionState, TermStatus, TermType
from app.services import clause_builder, stamp_guidance
from app.services.extractor import ResolvedTerm, Revision


def term(t: TermType, value: str, ids: list[int] | None = None) -> ResolvedTerm:
    return ResolvedTerm(
        type=t,
        value=value,
        source_message_ids=ids or [0],
        confidence=0.9,
        status=TermStatus.CLEAR,
    )


class TestClauseBuilder:
    def test_missing_terms_render_as_placeholders_never_guesses(self) -> None:
        agreement = clause_builder.build([term(TermType.SCOPE, "40 chairs")])
        price = next(c for c in agreement.clauses if c.id == "price")
        assert price.is_placeholder
        assert clause_builder.PLACEHOLDER in price.body

    def test_present_terms_carry_their_source_messages(self) -> None:
        agreement = clause_builder.build([term(TermType.PRICE, "4500 each", [4])])
        price = next(c for c in agreement.clauses if c.id == "price")
        assert price.source_message_ids == [4]
        assert "4500 each" in price.body

    def test_same_terms_give_the_same_hash(self) -> None:
        terms = [term(TermType.PRICE, "4500")]
        assert clause_builder.build(terms).clauses_hash == clause_builder.build(terms).clauses_hash

    def test_changing_a_value_changes_the_hash(self) -> None:
        a = clause_builder.build([term(TermType.PRICE, "4500")])
        b = clause_builder.build([term(TermType.PRICE, "4200")])
        assert a.clauses_hash != b.clauses_hash

    def test_revisions_appear_in_a_changes_clause(self) -> None:
        price = term(TermType.PRICE, "4200", [6])
        price.revision_state = RevisionState.SETTLED
        price.revision_history = [Revision(value="4500", source_message_ids=[3])]
        agreement = clause_builder.build([price])
        changes = next(c for c in agreement.clauses if c.id == "changes")
        assert "4500" in changes.body and "4200" in changes.body

    def test_conflicted_price_is_never_printed_as_agreed(self) -> None:
        price = term(TermType.PRICE, "4200 each", [6])
        price.status = TermStatus.CONFLICTED
        price.revision_state = RevisionState.UNRESOLVED
        price.revision_history = [Revision(value="4500 each", source_message_ids=[2])]
        clause = next(c for c in clause_builder.build([price]).clauses if c.id == "price")
        assert clause.is_placeholder
        assert "never confirmed" in clause.body
        assert "The agreed price is 4200" not in clause.body
        assert clause.source_message_ids == [2, 6]

    def test_unaccepted_change_is_not_listed_as_agreed(self) -> None:
        price = term(TermType.PRICE, "4200 each", [6])
        price.status = TermStatus.CONFLICTED
        price.revision_history = [Revision(value="4500 each", source_message_ids=[2])]
        ids = [c.id for c in clause_builder.build([price]).clauses]
        assert "changes" not in ids

    def test_notice_is_always_present(self) -> None:
        assert "not legal advice" in clause_builder.build([]).notice


class TestStampGuidance:
    def test_karnataka_is_supported_with_a_source(self) -> None:
        g = stamp_guidance.guidance_for("KA")
        assert g.supported and g.source_url and g.last_verified

    def test_no_rate_is_ever_invented(self) -> None:
        for code in ("KA", "MH"):
            assert stamp_guidance.guidance_for(code).duty_rate is None

    def test_unsupported_state_says_so_and_guesses_nothing(self) -> None:
        g = stamp_guidance.guidance_for("TN")
        assert not g.supported
        assert g.duty_rate is None
        assert "lawyer" in g.message

    def test_legal_effect_is_inadmissible_not_void(self) -> None:
        g = stamp_guidance.guidance_for("KA")
        assert "not void" in g.headline
        assert any(p["section"] == "s.42" for p in g.points)  # curable
