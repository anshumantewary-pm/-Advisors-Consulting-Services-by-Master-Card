import pytest

from cardwise.credit.decision import APPROVE, APPROVE_WITH_CONDITIONS, DECLINE, REFER, decide
from cardwise.credit.model import (
    BankPolicy,
    borrower_from_dict,
)
from tests.credit_helpers import borrower, load


def test_strong_borrower_is_approved() -> None:
    d = decide(borrower_from_dict(load("northwind-industrial")))
    assert d.decision == APPROVE
    assert d.rating.final.grade == 4
    assert d.approver == "Senior Credit Officer"
    assert not d.exceptions
    assert not d.hard_stops
    assert d.recommended_amount == pytest.approx(75e6)
    assert d.total_exposure == pytest.approx(95e6)
    assert d.covenants.max_leverage >= d.pro_forma.leverage  # type: ignore[operator]
    assert d.covenants.reporting == "semi-annually"
    weights = sum(f.weight for f in d.rating.factors)
    assert weights == pytest.approx(1.0)
    assert d.rating.score == pytest.approx(sum(f.contribution for f in d.rating.factors))


def test_stretched_borrower_is_referred() -> None:
    d = decide(borrower_from_dict(load("coastal-retail")))
    assert d.decision == REFER
    assert {c.key for c in d.exceptions} == {"leverage", "dscr", "payback"}
    assert d.approver == "Credit Committee"
    assert d.recommended_amount == 0
    assert any("Watchlist" in c for c in d.conditions)


def test_kyc_and_weak_credit_is_declined() -> None:
    d = decide(borrower_from_dict(load("meridian-energy")))
    assert d.decision == DECLINE
    assert {c.key for c in d.hard_stops} == {"kyc", "appetite", "dscr_hard"}
    assert d.approver == "n/a (declined)"
    assert any("KYC" in o for o in d.rating.overrides)
    assert any("EBITDA fell" in o for o in d.rating.overrides)
    assert any("Bullet" in r.risk for r in d.risks)


def test_one_exception_means_conditions_and_a_higher_approver() -> None:
    d = decide(borrower_from_dict(borrower(**{"request.tenor_years": 7})))
    assert d.decision == APPROVE_WITH_CONDITIONS
    assert [c.key for c in d.exceptions] == ["tenor"]
    assert d.approver == "Chief Credit Officer"
    assert any(c.startswith("Exception approved: Tenor") for c in d.conditions)


def test_grade_eight_is_referred_even_without_exceptions() -> None:
    policy = BankPolicy(worst_grade=4)
    d = decide(borrower_from_dict(load("northwind-industrial")), policy)
    assert d.decision == REFER
    assert d.reasons == ("Grade 4 needs committee sign-off",)


def test_negative_equity_and_loss_making_borrowers_are_notched() -> None:
    data = borrower()
    data["financials"][-1].update(equity=-1e6, ebitda=-2e6)
    d = decide(borrower_from_dict(data))
    assert d.rating.final.grade >= 8
    assert any("Negative equity" in o for o in d.rating.overrides)
    assert any("EBITDA is zero or negative" in o for o in d.rating.overrides)
    assert d.decision == DECLINE
