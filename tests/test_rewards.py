import pytest

from cardwise.core.errors import ValidationError
from cardwise.issuing.rewards import effective_rewards_rate, points_liability, rewards_programme


def test_effective_rate() -> None:
    assert effective_rewards_rate(1.5, 0.01, 0.2) == pytest.approx(0.012)


def test_programme_break_even_is_exact() -> None:
    r = rewards_programme(100_000, 12_000, 0.10, 1.0, 0.01, 0.25, 0.02, 0.002, 1e6)
    assert r.effective_rewards_rate == pytest.approx(0.0075)
    assert r.baseline_spend == pytest.approx(1.2e9)
    assert r.incremental_spend == pytest.approx(1.2e8)
    assert r.net_benefit == pytest.approx(r.incremental_margin - r.programme_cost)
    assert r.break_even_lift is not None
    at = rewards_programme(100_000, 12_000, r.break_even_lift, 1.0, 0.01, 0.25, 0.02, 0.002, 1e6)
    assert at.net_benefit == pytest.approx(0, abs=1e-3)


def test_programme_that_can_never_pay() -> None:
    r = rewards_programme(10, 100, 0.5, 3.0, 0.01, 0.0, 0.015)
    assert r.break_even_lift is None
    empty = rewards_programme(0, 100, 0.1, 1, 0.01, 0.1, 0.02)
    assert empty.roi is None
    assert empty.break_even_lift is None


def test_liability_and_validation() -> None:
    assert points_liability(1e9, 0.01, 0.15) == pytest.approx(8.5e6)
    with pytest.raises(ValidationError, match="breakage"):
        effective_rewards_rate(1, 0.01, 1.2)
    with pytest.raises(ValidationError, match="point_value"):
        points_liability(1, 0, 0.1)
