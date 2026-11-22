import pytest

from cardwise.core.errors import ValidationError
from cardwise.risk.rollrate import BUCKETS, analyse, bucket_shares, project, transition_matrix

MOVES = {
    "current": {"current": 970, "1-29": 30},
    "1-29": {"current": 60, "1-29": 10, "30-59": 30},
    "30-59": {"current": 20, "30-59": 20, "60-89": 60},
    "60-89": {"current": 10, "60-89": 20, "90-119": 70},
    "90-119": {"90-119": 20, "120-149": 80},
    "120-149": {"120-149": 10, "charge_off": 90},
}


def test_matrix_rows_sum_to_one_and_charge_off_absorbs() -> None:
    m = transition_matrix(MOVES)
    for row in m.values():
        assert sum(row.values()) == pytest.approx(1)
    assert m["charge_off"]["charge_off"] == 1


def test_analysis() -> None:
    a = analyse(MOVES, {"current": 1e9, "1-29": 3e7}, months=12)
    assert a.roll_rates["current"] == pytest.approx(0.03)
    assert a.flow_through == pytest.approx(0.03 * 0.3 * 0.6 * 0.7 * 0.8 * 0.9)
    assert len(a.projection) == 12
    total = sum(a.projection[-1].values())
    assert total == pytest.approx(1.03e9)
    assert 0 < a.loss_rate < 0.05
    assert a.projected_charge_offs == pytest.approx(a.projection[-1]["charge_off"])


def test_shares_and_errors() -> None:
    s = bucket_shares([90, 5, 2, 1, 1, 1, 0])
    assert s["current"] == pytest.approx(0.9)
    assert bucket_shares([0] * len(BUCKETS))["current"] == 0
    with pytest.raises(ValidationError, match="one per bucket"):
        bucket_shares([1, 2])
    with pytest.raises(ValidationError, match="unknown bucket"):
        transition_matrix({"current": {"180+": 1}})
    with pytest.raises(ValidationError, match="unknown bucket"):
        transition_matrix({"late": {"current": 1}})
    with pytest.raises(ValidationError, match="unknown bucket"):
        project({"late": 1}, transition_matrix(MOVES), 1)
    assert analyse({}, {}, 1).loss_rate == 0
