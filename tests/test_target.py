import pytest

from cardwise.advisory.diagnose import diagnose
from cardwise.advisory.target import target_state
from cardwise.core.errors import ValidationError
from tests.test_diagnose import REVIEW


def test_full_achievement_reaches_range_edges() -> None:
    d = diagnose(REVIEW)
    t = target_state(d, 1.0)
    e = t.economics
    assert e.net_credit_loss_rate == pytest.approx(0.05)
    assert e.rewards_rate == pytest.approx(0.008)
    assert e.active_accounts == pytest.approx(0.55 * 1_000_000)
    assert e.revolving_balances / e.receivables == pytest.approx(0.45)
    assert sum(t.bridge.drivers.values()) == pytest.approx(t.bridge.change)
    assert t.bridge.after > t.bridge.before
    assert t.roa_after > t.roa_before


def test_partial_and_per_kpi_achievement() -> None:
    d = diagnose(REVIEW)
    none = target_state(d, 0.0)
    assert none.bridge.change == pytest.approx(0)
    half = target_state(d, 0.5)
    full = target_state(d, 1.0)
    assert 0 < half.bridge.change < full.bridge.change
    only_losses = target_state(d, {"net_credit_loss_rate": 1.0})
    assert only_losses.bridge.change == pytest.approx(0.01 * 2.5e9)
    assert only_losses.achievement["rewards_rate"] == 0


def test_errors() -> None:
    d = diagnose(REVIEW)
    with pytest.raises(ValidationError, match="no opportunity"):
        target_state(d, {"roa": 1.0})
    with pytest.raises(ValidationError, match="achievement"):
        target_state(d, 1.5)
