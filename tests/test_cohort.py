import pytest

from cardwise.core.errors import ValidationError
from cardwise.customer.cohort import cohort_retention

ROWS = [
    ("a", 0, 0),
    ("a", 0, 1),
    ("a", 0, 2),
    ("b", 0, 0),
    ("b", 0, 2),
    ("c", 1, 1),
    ("c", 1, 2),
    ("d", 1, 1),
]


def test_table() -> None:
    t = cohort_retention(ROWS)
    assert t.cohorts == ("0", "1")
    assert t.sizes == {"0": 2, "1": 2}
    assert t.retention["0"] == (1.0, 0.5, 1.0)
    assert t.retention["1"] == (1.0, 0.5)
    assert t.average[1] == pytest.approx(0.5)
    assert t.average[2] == pytest.approx(1.0)


@pytest.mark.parametrize(
    ("rows", "message"),
    [
        ([], "no activity"),
        ([("a", 2, 1)], "before joining"),
        ([("a", 0, 0), ("a", 1, 1)], "two cohorts"),
    ],
)
def test_errors(rows: list[tuple[str, int, int]], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        cohort_retention(rows)
