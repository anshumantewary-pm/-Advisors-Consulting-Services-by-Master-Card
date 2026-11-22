import pytest

from cardwise.core.errors import ValidationError
from cardwise.issuing.portfolio import portfolio_kpis


def test_kpis() -> None:
    k = portfolio_kpis(1_000_000, 620_000, 6.2e9, 2.4e9, 1.2e9, transactions=124e6)
    assert k.active_rate == pytest.approx(0.62)
    assert k.spend_per_active == pytest.approx(10_000)
    assert k.balance_per_active == pytest.approx(2.4e9 / 620_000)
    assert k.revolve_rate == pytest.approx(0.5)
    assert k.average_ticket == pytest.approx(50)
    assert k.transactions_per_active == pytest.approx(200)


def test_empty_portfolio_does_not_divide_by_zero() -> None:
    k = portfolio_kpis(10, 0, 0, 0, 0)
    assert k.spend_per_active == 0
    assert k.revolve_rate == 0
    assert k.average_ticket is None
    assert k.transactions_per_active is None


@pytest.mark.parametrize(
    ("args", "message"),
    [((0, 0, 0, 0, 0), "accounts"), ((10, 11, 0, 0, 0), "active"), ((10, 5, 1, 1, 2), "revolving")],
)
def test_validation(args: tuple[float, ...], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        portfolio_kpis(*args)
