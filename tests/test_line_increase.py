import pytest

from cardwise.core.errors import ValidationError
from cardwise.issuing.line_increase import line_increase


def test_profit_adds_up() -> None:
    r = line_increase(50_000, 2000, 0.3, 0.6, 0.22, 0.045, 0.05, 1500, 0.002, 400, 0.017)
    assert r.new_limit == pytest.approx(100e6)
    assert r.new_balances == pytest.approx(30e6)
    assert r.interest == pytest.approx(30e6 * 0.6 * 0.22)
    assert r.existing_balance_losses == pytest.approx(50_000 * 1500 * 0.002)
    assert r.net_profit == pytest.approx(sum(s.value for s in r.steps[:-1]))
    assert r.profit_per_account == pytest.approx(r.net_profit / 50_000)
    assert r.break_even_loss_rate is not None
    at = line_increase(
        50_000, 2000, 0.3, 0.6, 0.22, 0.045, r.break_even_loss_rate, 1500, 0.002, 400, 0.017
    )
    assert at.net_profit == pytest.approx(0, abs=1e-6)


def test_no_take_up() -> None:
    r = line_increase(0, 1000, 0.5, 0.5, 0.2, 0.05, 0.05)
    assert r.break_even_loss_rate is None
    assert r.profit_per_account == 0
    with pytest.raises(ValidationError, match="utilisation"):
        line_increase(1, 1, 1.5, 0.5, 0.2, 0.05, 0.05)
