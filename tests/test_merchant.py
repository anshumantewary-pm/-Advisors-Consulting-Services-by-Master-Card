import pytest

from cardwise.acquiring.merchant import (
    ChargebackThresholds,
    approval_uplift_value,
    chargeback_status,
    merchant_kpis,
)
from cardwise.core.errors import ValidationError


def test_kpis() -> None:
    k = merchant_kpis(100_000, 92_000, 4.6e6, 700, chargeback_value=40_000,
                      declines_by_reason={"insufficient funds": 4000, "suspected fraud": 2000})
    assert k.approval_rate == pytest.approx(0.92)
    assert k.average_ticket == pytest.approx(50)
    assert k.chargeback_ratio == pytest.approx(700 / 92_000)
    assert k.chargeback_status == "early warning"
    assert k.chargeback_value_ratio == pytest.approx(40_000 / 4.6e6)
    assert k.decline_mix["insufficient funds"] == pytest.approx(0.5)
    assert k.lost_sales_value == pytest.approx(8000 * 50)


@pytest.mark.parametrize(
    ("ratio", "status"),
    [(0.001, "healthy"), (0.007, "early warning"), (0.01, "standard program"), (0.02, "excessive")],
)
def test_status_bands(ratio: float, status: str) -> None:
    assert chargeback_status(ratio) == status


def test_edge_cases_and_errors() -> None:
    k = merchant_kpis(10, 0, 0, 0, chargeback_value=0)
    assert k.average_ticket == 0
    assert k.decline_mix == {}
    assert k.chargeback_value_ratio == 0
    with pytest.raises(ValidationError, match="approvals"):
        merchant_kpis(10, 11, 0, 0)
    with pytest.raises(ValidationError, match="more than the declines"):
        merchant_kpis(10, 8, 1, 0, declines_by_reason={"x": 5})
    with pytest.raises(ValidationError, match="increase"):
        chargeback_status(0.01, ChargebackThresholds(0.02, 0.01, 0.03))


def test_approval_uplift() -> None:
    assert approval_uplift_value(1e6, 0.90, 0.93, 40, 0.3) == pytest.approx(1e6 * 0.03 * 40 * 0.3)
    assert approval_uplift_value(1e6, 0.95, 0.93, 40, 0.3) == 0
