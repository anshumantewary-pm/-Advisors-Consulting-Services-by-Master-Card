import pytest

from cardwise.core.errors import ValidationError
from cardwise.customer.rfm import Customer, quintile_scores, rfm, segment


def test_quintiles() -> None:
    assert quintile_scores([1, 2, 3, 4, 5]) == (1, 2, 3, 4, 5)
    assert quintile_scores([1, 2, 3, 4, 5], higher_is_better=False) == (5, 4, 3, 2, 1)
    assert quintile_scores([7, 7, 7, 7, 7]) == (1, 1, 1, 1, 1)
    assert quintile_scores(list(range(10))) == (1, 1, 2, 2, 3, 3, 4, 4, 5, 5)


@pytest.mark.parametrize(
    ("r", "f", "name"),
    [(5, 5, "Champions"), (3, 3, "Loyal"), (5, 1, "New / promising"), (1, 5, "Can't lose them"),
     (2, 2, "At risk"), (3, 1, "Needs attention"), (1, 1, "Hibernating")],
)
def test_segments(r: int, f: int, name: str) -> None:
    assert segment(r, f) == name


def test_rfm() -> None:
    customers = [Customer(str(i), 100 - 10 * i, i, 100 * i) for i in range(10)]
    res = rfm(customers)
    best = res.scores[-1]
    assert best.code == "555"
    assert best.segment == "Champions"
    assert sum(res.segment_counts.values()) == 10
    assert sum(res.segment_spend.values()) == pytest.approx(4500)
    with pytest.raises(ValidationError):
        rfm([])
    with pytest.raises(ValidationError, match="x.spend"):
        rfm([Customer("x", 1, 1, -1)])
