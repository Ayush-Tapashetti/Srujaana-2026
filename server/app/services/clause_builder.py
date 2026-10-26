"""Plain-language agreement construction (F4). No LLM, no templating engine.

The agreement is a list of clause objects, not a rendered string:

    {"id": "price", "heading": "Price", "body": "...",
     "status": "clear", "source_message_ids": [4, 11]}

React renders them. Keeping one representation means the clause text and
its source links cannot drift apart, and it is what lets F5 and F6 hash
exactly what the counterparty was shown.

Nothing here invents a value. An unresolved term renders as
[to be confirmed] and stays that way until the owner fills it in.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from app.models.analysis import TermStatus, TermType
from app.services.evidence_chain import canonical_hash
from app.services.extractor import ResolvedTerm

PLACEHOLDER = "[to be confirmed]"
PENDING_BADGE = "[Pending Mutual Confirmation]"

NOT_LEGAL_ADVICE = (
    "This document was prepared from a chat conversation to help both sides "
    "agree on what was said. It is decision support, not legal advice, and "
    "it has not been reviewed by a lawyer."
)


@dataclass(slots=True)
class Clause:
    id: str
    heading: str
    body: str
    status: str
    source_message_ids: list[int] = field(default_factory=list)
    is_placeholder: bool = False


@dataclass(slots=True)
class Agreement:
    clauses: list[Clause]
    summary: str
    notice: str
    clauses_hash: str

    def as_dicts(self) -> list[dict]:
        return [asdict(c) for c in self.clauses]


def hash_clauses(clauses: list[dict]) -> str:
    """The fingerprint of the clause text and status (same rule as build)."""
    return canonical_hash(
        {"clauses": [{"id": c["id"], "body": c["body"], "status": c["status"]} for c in clauses]}
    )


def render_clause_body(clause) -> str:
    """Clause text, with the pending badge when an edit awaits the other side.

    Accepts a Clause, a dict or a ClauseOut. Never alters the stored clause.
    """
    get = clause.get if isinstance(clause, dict) else lambda k, d=None: getattr(clause, k, d)
    if get("is_pending", False):
        return f"{get('body', '')} {PENDING_BADGE}"
    return get("body", "")


def _index(terms: list[ResolvedTerm]) -> dict[TermType, list[ResolvedTerm]]:
    out: dict[TermType, list[ResolvedTerm]] = {}
    for term in terms:
        out.setdefault(term.type, []).append(term)
    return out


def _first(by_type, term_type: TermType) -> ResolvedTerm | None:
    group = by_type.get(term_type)
    return group[0] if group else None


def _clause(
    clause_id: str,
    heading: str,
    term: ResolvedTerm | None,
    render,
    empty_text: str,
) -> Clause:
    if term is None:
        return Clause(
            id=clause_id,
            heading=heading,
            body=f"{empty_text} {PLACEHOLDER}.",
            status=TermStatus.MISSING.value,
            source_message_ids=[],
            is_placeholder=True,
        )
    if term.status is TermStatus.CONFLICTED:
        # Never print an unagreed value as agreed. Show both sides instead,
        # so whoever reads this sees exactly where the disagreement is.
        earlier = term.revision_history[-1].value if term.revision_history else None
        detail = (
            f"{earlier} was agreed earlier; {term.value} was proposed later "
            "and never confirmed"
            if earlier
            else f"{term.value} was proposed and never confirmed"
        )
        return Clause(
            id=clause_id,
            heading=heading,
            body=f"{empty_text} {PLACEHOLDER} ({detail}).",
            status=term.status.value,
            source_message_ids=sorted(
                set(term.source_message_ids)
                | {i for r in term.revision_history for i in r.source_message_ids}
            ),
            is_placeholder=True,
        )
    return Clause(
        id=clause_id,
        heading=heading,
        body=render(term.value),
        status=term.status.value,
        source_message_ids=term.source_message_ids,
        is_placeholder=False,
    )


def build(terms: list[ResolvedTerm]) -> Agreement:
    by_type = _index(terms)
    parties = by_type.get(TermType.PARTY, [])

    clauses: list[Clause] = []

    # 1. Parties
    if parties:
        names = " and ".join(p.value for p in parties)
        body = f"This is an agreement between {names}."
        if len(parties) == 1:
            body += f" The other party is {PLACEHOLDER}."
        clauses.append(
            Clause(
                id="parties",
                heading="Parties",
                body=body,
                status="clear" if len(parties) >= 2 else TermStatus.MISSING.value,
                source_message_ids=sorted(
                    {i for p in parties for i in p.source_message_ids}
                ),
                is_placeholder=len(parties) < 2,
            )
        )
    else:
        clauses.append(
            Clause(
                id="parties",
                heading="Parties",
                body=f"This is an agreement between {PLACEHOLDER} and {PLACEHOLDER}.",
                status=TermStatus.MISSING.value,
                is_placeholder=True,
            )
        )

    # 2. Scope, with quantity folded in where we have it
    scope = _first(by_type, TermType.SCOPE)
    quantity = _first(by_type, TermType.QUANTITY)
    if scope is not None:
        body = f"The supplier will provide {scope.value}."
        if quantity is not None:
            # "45 chairs" already names the item, so avoid "45 chairs of chairs".
            if scope.value.lower() in quantity.value.lower():
                body = f"The supplier will provide {quantity.value}."
            else:
                body = f"The supplier will provide {quantity.value} ({scope.value})."
        sources = sorted(
            set(scope.source_message_ids)
            | set(quantity.source_message_ids if quantity else [])
        )
        clauses.append(
            Clause(
                id="scope",
                heading="What is being supplied",
                body=body,
                status=scope.status.value,
                source_message_ids=sources,
            )
        )
    else:
        clauses.append(
            Clause(
                id="scope",
                heading="What is being supplied",
                body=f"The supplier will provide {PLACEHOLDER}.",
                status=TermStatus.MISSING.value,
                is_placeholder=True,
            )
        )

    # 3. Price, with advance appended where present
    price = _first(by_type, TermType.PRICE)
    advance = _first(by_type, TermType.ADVANCE)
    price_clause = _clause(
        "price",
        "Price",
        price,
        lambda v: f"The agreed price is {v}.",
        "The agreed price is",
    )
    if advance is not None and price is not None:
        price_clause.body += f" An advance of {advance.value} applies."
        price_clause.source_message_ids = sorted(
            set(price_clause.source_message_ids) | set(advance.source_message_ids)
        )
    clauses.append(price_clause)

    # 4-8
    clauses.append(
        _clause(
            "payment",
            "Payment",
            _first(by_type, TermType.PAYMENT_DUE),
            lambda v: f"Payment is due {v}.",
            "Payment is due",
        )
    )
    clauses.append(
        _clause(
            "timeline",
            "Delivery",
            _first(by_type, TermType.DELIVERY_DATE),
            lambda v: f"Delivery or completion is due {v}.",
            "Delivery or completion is due",
        )
    )
    clauses.append(
        _clause(
            "acceptance",
            "Acceptance",
            _first(by_type, TermType.ACCEPTANCE),
            lambda v: f"The work is accepted when {v}.",
            "The work is accepted when",
        )
    )
    clauses.append(
        _clause(
            "cancellation",
            "Changes and cancellation",
            _first(by_type, TermType.CANCELLATION),
            lambda v: f"If the order is cancelled or payment is late: {v}.",
            "If the order is cancelled or payment is late:",
        )
    )
    clauses.append(
        _clause(
            "disputes",
            "If something goes wrong",
            _first(by_type, TermType.DISPUTE),
            lambda v: f"Disagreements will be handled as follows: {v}.",
            "Disagreements will be handled as follows:",
        )
    )

    # "Changes agreed" records accepted revisions only, so an earlier value is
    # visible rather than quietly replaced. An unaccepted change is NOT listed
    # here: its own clause already shows both values as unconfirmed, and
    # listing it under "agreed" would contradict that.
    revised = [
        t for t in terms if t.revision_history and t.status is not TermStatus.CONFLICTED
    ]
    if revised:
        lines = []
        for term in revised:
            previous = ", ".join(r.value for r in term.revision_history)
            lines.append(
                f"{term.type.value.replace('_', ' ')}: earlier value(s) "
                f"{previous}; current value {term.value}"
            )
        clauses.append(
            Clause(
                id="changes",
                heading="Changes agreed along the way",
                body="These terms changed during the conversation. " + "; ".join(lines) + ".",
                status="clear",
                source_message_ids=sorted(
                    {
                        i
                        for t in revised
                        for r in t.revision_history
                        for i in r.source_message_ids
                    }
                ),
            )
        )

    present = [c for c in clauses if not c.is_placeholder]
    summary = (
        f"We read {len(present)} of {len(clauses)} terms from your chat. "
        "Anything marked [to be confirmed] was never agreed in the messages, "
        "so please fill it in before sending."
    )

    # Hash only what is legally meaningful: the clause text and its status.
    # Headings are presentation, so renaming one must not invalidate an
    # acknowledgement the counterparty already gave.
    return Agreement(
        clauses=clauses,
        summary=summary,
        notice=NOT_LEGAL_ADVICE,
        clauses_hash=hash_clauses([asdict(c) for c in clauses]),
    )
