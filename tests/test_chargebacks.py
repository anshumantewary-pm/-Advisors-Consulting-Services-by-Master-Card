import pytest

from cardwise.acquiring.chargebacks import chargeback_cost
from cardwise.core.errors import ValidationError


def test_cost_and_recovery() -> None:
    c = chargeback_cost(1000, 80, 15, 10, 0.6, 0.4, 20)
    assert c.gross_loss == pytest.approx(80_000)
    assert c.fees == pytest.approx(15_000)
    assert c.handling_cost == pytest.approx(10_000 + 600 * 20)
    assert c.recovered == pytest.approx(600 * 0.4 * 80)
    assert c.net_loss == pytest.approx(80_000 + 15_000 + 22_000 - 19_200)
    assert c.contest_recommended
    assert c.representment_net_value == pytest.approx(600 * (0.4 * 80 - 20))


def test_not_worth_contesting_cheap_digital_goods() -> None:
    c = chargeback_cost(100, 10, 15, 5, 1.0, 0.3, 20, goods_lost_share=0.2)
    assert not c.contest_recommended
    assert chargeback_cost(0, 10, 15, 5, 1, 1, 1).cost_per_chargeback == 0


def test_validation() -> None:
    with pytest.raises(ValidationError, match="win_rate"):
        chargeback_cost(1, 1, 1, 1, 0.5, 2, 1)
