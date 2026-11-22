import pytest

from cardwise.core.errors import ValidationError
from cardwise.risk.fraud import Scored, best_threshold, fraud_rate_bps, rule_economics


def test_bps() -> None:
    assert fraud_rate_bps(50_000, 100e6) == pytest.approx(5.0)
    assert fraud_rate_bps(0, 0) == 0


def test_rule_economics() -> None:
    r = rule_economics(80, 400, 20, 99_500, 300, 60, 0.03, churn_cost_per_false_decline=5)
    assert r.precision == pytest.approx(80 / 480)
    assert r.recall == pytest.approx(0.8)
    assert r.false_positive_ratio == pytest.approx(5)
    assert r.decline_rate == pytest.approx(480 / 100_000)
    assert r.fraud_prevented == pytest.approx(24_000)
    assert r.insult_cost == pytest.approx(400 * (1.8 + 5))
    assert r.total_cost == pytest.approx(20 * 300 + 400 * 6.8)


def test_rule_economics_empty() -> None:
    r = rule_economics(0, 0, 0, 0, 1, 1, 0.1)
    assert r.precision == r.recall == r.decline_rate == 0
    assert r.false_positive_ratio is None


def test_best_threshold() -> None:
    txns = [Scored(0.9, True, 500), Scored(0.8, True, 300), Scored(0.7, False, 100),
            Scored(0.4, False, 100), Scored(0.3, True, 20), Scored(0.1, False, 50)]
    choice = best_threshold(txns, margin=0.1, churn_cost_per_false_decline=10)
    assert choice.threshold == 0.8
    assert choice.fraud_missed == pytest.approx(20)
    assert choice.insult_cost == 0
    assert choice.recall == pytest.approx(2 / 3)
    assert len(choice.curve) == 7
    assert min(c for _, c in choice.curve) == pytest.approx(choice.total_cost)


def test_best_threshold_without_fraud_declines_nothing() -> None:
    choice = best_threshold([Scored(0.5, False, 10)], margin=0.2)
    assert choice.threshold == float("inf")
    assert choice.recall == 0
    with pytest.raises(ValidationError, match="transactions"):
        best_threshold([], 0.1)
