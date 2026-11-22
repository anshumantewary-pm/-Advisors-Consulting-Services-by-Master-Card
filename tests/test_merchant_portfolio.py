import pytest

from cardwise.acquiring.portfolio import Merchant, merchant_portfolio
from cardwise.core.errors import ValidationError

MERCHANTS = [
    Merchant("Grocer", 50e6, 0.008, 0.005, 0.0012, 20_000),
    Merchant("Boutique", 2e6, 0.022, 0.006, 0.0015, 3_000),
    Merchant("Airline", 30e6, 0.007, 0.0065, 0.0013, 15_000),
]


def test_portfolio() -> None:
    p = merchant_portfolio(MERCHANTS, target_bps=5)
    grocer = next(m for m in p.merchants if m.name == "Grocer")
    assert grocer.margin == pytest.approx(50e6 * 0.0018)
    assert grocer.contribution == pytest.approx(90_000 - 20_000)
    assert grocer.contribution_bps == pytest.approx(14)
    assert grocer.repriced_mdr is None
    airline = p.merchants[0]
    assert airline.name == "Airline"
    assert airline.contribution < 0
    assert airline.repriced_mdr == pytest.approx(0.0065 + 0.0013 + 15_000 / 30e6 + 0.0005)
    assert p.loss_makers == ("Airline",)
    assert p.repricing_uplift == pytest.approx(0.0005 * 30e6 - airline.contribution)
    assert p.total_contribution == pytest.approx(sum(m.contribution for m in p.merchants))
    assert p.concentration_top5 == pytest.approx(1.0)


def test_edge_cases() -> None:
    p = merchant_portfolio([Merchant("Idle", 0, 0.01, 0.005, 0.001, 500)])
    assert p.merchants[0].contribution_bps == 0
    assert p.concentration_top5 == 0
    with pytest.raises(ValidationError, match="at least one"):
        merchant_portfolio([])
    with pytest.raises(ValidationError, match=r"X\.mdr"):
        merchant_portfolio([Merchant("X", 1, 2, 0, 0)])
