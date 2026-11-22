import pytest

from cardwise.benchmark.ranges import PORTFOLIO_TYPES, KPIRange, get_portfolio_type
from cardwise.core.errors import UnknownNameError


def test_ranges_are_consistent() -> None:
    for t in PORTFOLIO_TYPES.values():
        keys = [r.key for r in t.ranges]
        assert len(keys) == len(set(keys))
        for r in t.ranges:
            assert r.low <= r.high


def test_status_and_weakness() -> None:
    good = KPIRange("x", "X", 0.5, 0.7, True)
    assert good.status(0.4) == "below"
    assert good.status(0.6) == "within"
    assert good.status(0.8) == "above"
    assert good.is_weak(0.4)
    assert not good.is_weak(0.8)
    bad = KPIRange("y", "Y", 0.02, 0.05, False)
    assert bad.is_weak(0.06)
    assert not bad.is_weak(0.01)


def test_lookup() -> None:
    t = get_portfolio_type("mass_credit")
    assert t.get("roa") is not None
    assert t.get("nope") is None
    with pytest.raises(UnknownNameError, match="unknown portfolio type"):
        get_portfolio_type("gold")
