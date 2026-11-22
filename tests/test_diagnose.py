import dataclasses

import pytest

from cardwise.advisory.diagnose import LEVERS, OUTCOMES, PortfolioReview, diagnose
from cardwise.benchmark.ranges import PORTFOLIO_TYPES
from cardwise.issuing.pnl import CardEconomics

ECON = CardEconomics(
    active_accounts=500_000,
    purchase_volume=5e9,
    receivables=2.5e9,
    revolving_balances=1.0e9,
    interchange_rate=0.017,
    apr=0.21,
    fee_income=40e6,
    rewards_rate=0.010,
    net_credit_loss_rate=0.06,
)
REVIEW = PortfolioReview(
    "Demo Bank",
    "mass_credit",
    1_000_000,
    ECON,
    transactions=100e6,
    approval_rate=0.82,
    fraud_losses=3e6,
)


def test_every_kpi_in_every_type_has_levers_or_is_an_outcome() -> None:
    for t in PORTFOLIO_TYPES.values():
        for r in t.ranges:
            assert (r.key in LEVERS) != (r.key in OUTCOMES)


def test_diagnosis_finds_and_sizes_gaps() -> None:
    d = diagnose(REVIEW)
    weak = {c.key for c in d.checks if c.weak}
    assert {
        "active_rate",
        "revolve_rate",
        "net_credit_loss_rate",
        "rewards_rate",
        "approval_rate",
    } <= weak
    by_key = {o.key: o for o in d.opportunities}
    assert by_key["net_credit_loss_rate"].annual_value == pytest.approx(0.01 * 2.5e9)
    assert by_key["rewards_rate"].annual_value == pytest.approx(0.002 * 5e9)
    assert by_key["revolve_rate"].annual_value == pytest.approx(0.05 * 2.5e9 * (0.21 - 0.06))
    values = [o.annual_value for o in d.opportunities]
    assert values == sorted(values, reverse=True)
    assert 0 <= d.health_score < 50
    assert "fraud_bps" not in weak
    assert d.total_opportunity == pytest.approx(sum(o.annual_value for o in d.opportunities))
    roa = next(c for c in d.checks if c.key == "roa")
    assert roa.weak
    assert "roa" not in by_key
    assert all("a year before tax" in o.detail for o in d.opportunities)


def test_strong_portfolio_has_strengths_and_no_gaps() -> None:
    econ = dataclasses.replace(
        ECON,
        active_accounts=800_000,
        revolving_balances=1.6e9,
        net_credit_loss_rate=0.02,
        rewards_rate=0.002,
        fee_income=150e6,
    )
    d = diagnose(dataclasses.replace(REVIEW, economics=econ, approval_rate=0.95, fraud_losses=1e6))
    assert not d.opportunities
    assert d.health_score == 100
    assert d.strengths
    assert d.total_opportunity == 0


def test_optional_inputs_are_skipped() -> None:
    d = diagnose(dataclasses.replace(REVIEW, approval_rate=None, fraud_losses=None))
    assert {"approval_rate", "fraud_bps"}.isdisjoint(c.key for c in d.checks)


def test_high_fraud_is_sized_in_basis_points() -> None:
    d = diagnose(dataclasses.replace(REVIEW, fraud_losses=6e6))  # 12 bp vs an 8 bp ceiling
    fraud = next(o for o in d.opportunities if o.key == "fraud_bps")
    assert fraud.annual_value == pytest.approx(4 / 1e4 * 5e9)
    assert "12.0 bp" in fraud.detail
