import pytest

from cardwise.core.errors import ValidationError
from cardwise.customer.clv import lifetime_value, portfolio_value, segment_values


def test_clv_formula_matches_series() -> None:
    v = lifetime_value(200, 0.85, 0.10)
    series = sum(200 * 0.85**t / 1.10 ** (t + 1) for t in range(2000))
    assert v.clv == pytest.approx(series)
    assert v.expected_lifetime_years == pytest.approx(1 / 0.15)
    assert v.max_acquisition_cost == pytest.approx(v.clv / 3)


def test_perpetual_and_zero_ratio() -> None:
    assert lifetime_value(100, 1.0, 0.1).clv == pytest.approx(1000)
    assert lifetime_value(100, 1.0, 0.0).clv == float("inf")
    assert lifetime_value(100, 0.5, 0.0, target_ltv_to_cac=0).max_acquisition_cost == float("inf")


def test_segments() -> None:
    segs = {"premium": (1000, 400, 0.9), "mass": (10_000, 60, 0.75)}
    vals = segment_values(segs, 0.1)
    assert vals["premium"].clv > vals["mass"].clv
    assert portfolio_value(segs, 0.1) == pytest.approx(
        1000 * vals["premium"].clv + 10_000 * vals["mass"].clv
    )
    with pytest.raises(ValidationError, match="retention"):
        lifetime_value(1, 1.5, 0.1)
    with pytest.raises(ValidationError, match=r"x\.customers"):
        segment_values({"x": (-1, 1, 0.5)}, 0.1)
