import pytest

from cardwise.core.errors import ValidationError
from cardwise.customer.retention import RetentionSegment, retention_plan

SEGMENTS = [
    RetentionSegment("premium at risk", 2000, 0.30, 1200, 40, 0.25),
    RetentionSegment("mass at risk", 20000, 0.20, 150, 15, 0.20),
    RetentionSegment("low value", 5000, 0.5, 20, 30, 0.5),
]


def test_plan() -> None:
    plan = retention_plan(SEGMENTS)
    by = {d.name: d for d in plan.decisions}
    assert by["premium at risk"].value_per_customer == pytest.approx(0.3 * 0.25 * 1200 - 40)
    assert by["premium at risk"].target
    assert not by["mass at risk"].target
    assert by["mass at risk"].break_even_save_rate == pytest.approx(15 / (0.2 * 150))
    assert by["low value"].break_even_save_rate is None
    assert plan.decisions[0].name == "premium at risk"
    assert plan.customers_targeted == 2000
    assert plan.budget == pytest.approx(80_000)
    assert plan.expected_value == pytest.approx(2000 * 50)
    assert plan.customers_saved == pytest.approx(2000 * 0.075)


def test_errors_and_zero_value() -> None:
    with pytest.raises(ValidationError, match="at least one"):
        retention_plan([])
    with pytest.raises(ValidationError, match=r"x\.save_rate"):
        retention_plan([RetentionSegment("x", 1, 0.1, 1, 1, 2)])
    plan = retention_plan([RetentionSegment("none", 10, 0.0, 100, 1, 0.5)])
    assert plan.decisions[0].break_even_save_rate is None
