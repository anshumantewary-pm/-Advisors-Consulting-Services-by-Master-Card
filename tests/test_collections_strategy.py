import pytest

from cardwise.core.errors import ValidationError
from cardwise.risk.collections import collections_strategy


def test_strategy() -> None:
    c = collections_strategy(120e6, 40_000, 0.70, 0.76, 0.55, 12)
    assert c.losses_before == pytest.approx(120e6 * 0.30 * 0.55)
    assert c.losses_avoided == pytest.approx(120e6 * 0.06 * 0.55)
    assert c.strategy_cost == pytest.approx(480_000)
    assert c.net_benefit == pytest.approx(c.losses_avoided - 480_000)
    assert c.break_even_cure_uplift == pytest.approx(480_000 / (120e6 * 0.55))
    assert c.roi is not None


def test_edge_cases() -> None:
    c = collections_strategy(0, 0, 0.5, 0.5, 0.5, 0)
    assert c.roi is None
    assert c.break_even_cure_uplift is None
    with pytest.raises(ValidationError, match="below baseline"):
        collections_strategy(1, 1, 0.6, 0.5, 0.5, 1)
