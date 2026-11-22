import pytest

from cardwise.core.errors import ValidationError
from cardwise.risk.provision import lifetime_pd, provision

BAL = {"current": 1000.0, "1-29": 50.0, "30-59": 20.0, "60-89": 10.0, "90-119": 8.0}
PD = {"current": 0.02, "1-29": 0.15, "30-59": 0.40, "60-89": 0.60}


def test_lifetime_pd() -> None:
    assert lifetime_pd(0.1, 2) == pytest.approx(0.19)
    with pytest.raises(ValidationError):
        lifetime_pd(0.1, 0)


def test_provision() -> None:
    p = provision(BAL, PD, lgd=0.85, lifetime_years=2)
    assert p.stage_balances == {"stage 1": 1050, "stage 2": 30, "stage 3": 8}
    s1 = (1000 * 0.02 + 50 * 0.15) * 0.85
    s2 = (20 * (1 - 0.6**2) + 10 * (1 - 0.4**2)) * 0.85
    s3 = 8 * 0.85
    assert p.stage_ecl["stage 1"] == pytest.approx(s1)
    assert p.stage_ecl["stage 2"] == pytest.approx(s2)
    assert p.stage_ecl["stage 3"] == pytest.approx(s3)
    assert p.ifrs9_ecl == pytest.approx(s1 + s2 + s3)
    assert p.lifetime_ecl > p.ifrs9_ecl
    assert p.coverage == pytest.approx(p.ifrs9_ecl / 1088)


@pytest.mark.parametrize(
    ("balances", "pds", "message"),
    [
        ({"180+": 1.0}, {}, "unknown bucket"),
        ({"current": 1.0}, {}, "no value"),
        ({}, {}, "must not be empty"),
    ],
)
def test_errors(balances: dict[str, float], pds: dict[str, float], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        provision(balances, pds, 0.8)


def test_zero_balances() -> None:
    p = provision({"current": 0.0}, {"current": 0.01}, 0.8)
    assert p.coverage == 0
    assert p.lifetime_coverage == 0
