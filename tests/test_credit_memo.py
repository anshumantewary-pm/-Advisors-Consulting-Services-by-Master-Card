from cardwise.credit.decision import decide
from cardwise.credit.memo import render_memo
from cardwise.credit.model import (
    borrower_from_dict,
)
from tests.credit_helpers import borrower, load


def test_low_margin_is_flagged_and_repriced() -> None:
    d = decide(borrower_from_dict(borrower(**{"request.margin": 0.004, "request.upfront_fee": 0})))
    assert "raroc" in {c.key for c in d.exceptions}
    assert d.recommended_margin == d.returns.required_margin
    assert "Margin needed to meet the hurdle" in render_memo(d)


def test_amount_is_capped_by_policy_capacity() -> None:
    d = decide(borrower_from_dict(borrower(**{"request.amount": 250e6})))
    assert d.recommended_amount < 250e6
    assert "Amount that fits policy" in render_memo(d)


def test_memo_contains_every_section_and_matches_the_decision() -> None:
    d = decide(borrower_from_dict(load("northwind-industrial")))
    memo = render_memo(d)
    for n in range(1, 13):
        assert f"## {n}. " in memo
    assert f"**Recommendation: {d.decision}**" in memo
    assert "FY2024 pro forma" in memo
    assert "Freehold plants (UK)" in memo


def test_memo_without_collateral_or_description() -> None:
    data = borrower(collateral=[], description="")
    data["request"]["seniority"] = "senior_unsecured"
    memo = render_memo(decide(borrower_from_dict(data)))
    assert "No business description supplied." in memo
