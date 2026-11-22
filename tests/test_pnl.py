import dataclasses

import pytest

from cardwise.core.errors import ValidationError
from cardwise.issuing.pnl import CardEconomics, card_pnl

BASE = CardEconomics(
    active_accounts=600_000,
    purchase_volume=6e9,
    receivables=2.4e9,
    revolving_balances=1.2e9,
    fee_income=60e6,
)


def test_lines_add_up() -> None:
    p = card_pnl(BASE)
    assert p.interchange == pytest.approx(108e6)
    assert p.interest == pytest.approx(240e6)
    assert p.revenue == pytest.approx(408e6)
    costs = p.funding_cost + p.rewards_cost + p.credit_losses + p.network_fees + p.operating_cost
    assert p.pre_tax_profit == pytest.approx(p.revenue - costs)
    assert p.steps[-1].value == pytest.approx(p.pre_tax_profit)
    assert sum(p.revenue_mix.values()) == pytest.approx(1.0)
    assert p.roa == pytest.approx(p.pre_tax_profit / 2.4e9)
    assert p.profit_per_active == pytest.approx(p.pre_tax_profit / 600_000)
    assert p.risk_adjusted_revenue == pytest.approx(p.revenue - p.funding_cost - p.credit_losses)


def test_zero_revenue_mix() -> None:
    p = card_pnl(dataclasses.replace(BASE, purchase_volume=0, revolving_balances=0, fee_income=0))
    assert p.revenue_mix == {"interchange": 0.0, "interest": 0.0, "fees": 0.0}


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("active_accounts", 0),
        ("receivables", 0),
        ("apr", 1.5),
        ("fee_income", -1),
        ("cost_per_account", -1),
        ("purchase_volume", -1),
    ],
)
def test_validation(field: str, value: float) -> None:
    with pytest.raises(ValidationError, match=field):
        card_pnl(dataclasses.replace(BASE, **{field: value}))


def test_bridge_adds_up() -> None:
    from cardwise.issuing.pnl import pnl_bridge

    after = dataclasses.replace(BASE, purchase_volume=6.6e9, net_credit_loss_rate=0.045)
    b = pnl_bridge(BASE, after)
    assert sum(b.drivers.values()) == pytest.approx(b.change)
    assert b.drivers["credit_losses"] == pytest.approx(-0.01 * 2.4e9)
    assert b.drivers["interchange"] > 0
    assert b.drivers["fees"] == 0
