import math

import pytest

from cardwise.core.errors import ValidationError
from cardwise.core.validate import (
    require_count,
    require_fraction,
    require_non_empty,
    require_non_negative,
    require_number,
    require_numbers,
    require_positive,
    require_rate,
)


def test_accepts_good_values() -> None:
    assert require_number("x", -3) == -3.0
    assert require_non_negative("x", 0) == 0.0
    assert require_positive("x", 2) == 2.0
    assert require_fraction("x", 1) == 1.0
    assert require_rate("x", -0.5) == -0.5
    assert require_count("n", 3) == 3
    assert require_numbers("xs", [1, 2.5]) == (1.0, 2.5)
    require_non_empty("xs", [1])


@pytest.mark.parametrize(
    ("fn", "value"),
    [
        (require_number, "1"),
        (require_number, True),
        (require_number, math.nan),
        (require_number, math.inf),
        (require_non_negative, -1),
        (require_positive, 0),
        (require_fraction, 1.1),
        (require_rate, -1),
        (require_count, 0),
        (require_count, 1.5),
        (require_numbers, "12"),
        (require_numbers, []),
        (require_numbers, [1, "a"]),
    ],
)
def test_rejects_bad_values(fn: object, value: object) -> None:
    with pytest.raises(ValidationError, match="x"):
        fn("x", value)  # type: ignore[operator]


def test_empty_sequence() -> None:
    with pytest.raises(ValidationError, match="must not be empty"):
        require_non_empty("rows", [])
