import pytest

from cardwise.credit.rating import MASTER_SCALE, grade, grade_for_score, scale


def test_master_scale_is_monotonic() -> None:
    pds = [g.pd for g in MASTER_SCALE]
    assert pds == sorted(pds)
    assert [g.grade for g in MASTER_SCALE] == list(range(1, 11))
    assert grade(0).grade == 1
    assert grade(42).grade == 10


def test_scale_and_grade_bands() -> None:
    assert scale(None, 0, 1) == 0
    assert scale(6.0, 6.0, 1.0) == 0
    assert scale(0.5, 6.0, 1.0) == 100
    assert scale(3.5, 6.0, 1.0) == pytest.approx(50)
    assert scale(100e6, 10e6, 1e9, log=True) == pytest.approx(50)
    assert grade_for_score(90) == 1
    assert grade_for_score(61) == 4
    assert grade_for_score(10) == 9
