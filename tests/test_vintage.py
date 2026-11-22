import pytest

from cardwise.core.errors import ValidationError
from cardwise.risk.vintage import Vintage, lifetime_loss_estimate, vintage_curves

V1 = Vintage("2024-Q1", 100e6, (0, 0.1e6, 0.3e6, 0.5e6, 0.6e6))
V2 = Vintage("2024-Q2", 50e6, (0, 0.2e6, 0.4e6))


def test_curves() -> None:
    vc = vintage_curves([V1, V2])
    assert vc.at_month == 3
    assert vc.loss_at_month["2024-Q1"] == pytest.approx(0.004)
    assert vc.loss_at_month["2024-Q2"] == pytest.approx(0.012)
    assert vc.worst == "2024-Q2"
    assert vc.best == "2024-Q1"
    assert vc.average_curve[1] == pytest.approx((0.001 * 100 + 0.004 * 50) / 150)
    assert vc.average_curve[4] == pytest.approx(vc.curves["2024-Q1"][4])


def test_lifetime_estimate() -> None:
    assert lifetime_loss_estimate([0.01, 0.02], {2: 0.25}) == pytest.approx(0.08)


@pytest.mark.parametrize(
    ("call", "message"),
    [
        (lambda: vintage_curves([]), "at least one"),
        (lambda: vintage_curves([V1, V1]), "unique"),
        (lambda: vintage_curves([Vintage("x", 1, ())]), "at least one month"),
        (lambda: vintage_curves([V1], at_month=9), "at_month"),
        (lambda: vintage_curves([Vintage("x", 0, (1,))]), "originated"),
        (lambda: lifetime_loss_estimate([], {}), "empty"),
        (lambda: lifetime_loss_estimate([0.1], {}), "no entry"),
        (lambda: lifetime_loss_estimate([0.1], {1: 0}), "shares"),
    ],
)
def test_errors(call: object, message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        call()  # type: ignore[operator]
