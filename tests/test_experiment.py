import pytest

from cardwise.core.errors import ValidationError
from cardwise.customer.experiment import sample_size, two_proportion_test


def test_significant_lift() -> None:
    r = two_proportion_test(10_000, 1200, 10_000, 1000, value_per_conversion=50)
    assert r.absolute_lift == pytest.approx(0.02)
    assert r.relative_lift == pytest.approx(0.2)
    assert r.z == pytest.approx(4.5, abs=0.1)
    assert r.p_value < 0.001
    assert r.significant
    assert r.ci_low < 0.02 < r.ci_high
    assert r.incremental_responders == pytest.approx(200)
    assert r.incremental_value == pytest.approx(10_000)


def test_no_difference() -> None:
    r = two_proportion_test(100, 0, 100, 0)
    assert r.z == 0
    assert not r.significant
    assert r.relative_lift is None


def test_sample_size() -> None:
    n = sample_size(0.10, 0.02)
    assert 3800 < n < 3900  # textbook value is about 3,841 per arm
    assert sample_size(0.10, 0.02, power=0.9) > n


@pytest.mark.parametrize(
    "call",
    [
        lambda: two_proportion_test(10, 11, 10, 1),
        lambda: two_proportion_test(10, 1, 10, 1, confidence=1.0),
        lambda: sample_size(0.99, 0.02),
        lambda: sample_size(0.1, 0.02, power=1.0),
    ],
)
def test_errors(call: object) -> None:
    with pytest.raises(ValidationError):
        call()  # type: ignore[operator]
