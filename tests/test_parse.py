from dataclasses import dataclass

import pytest

from cardwise.core.errors import ValidationError
from cardwise.core.parse import from_dict


@dataclass(frozen=True)
class Inner:
    x: float


@dataclass(frozen=True)
class Thing:
    name: str
    amount: float
    count: int = 1
    flag: bool = False
    note: str | None = None
    inner: Inner | None = None


def test_builds_and_coerces() -> None:
    t = from_dict(Thing, {"name": "a", "amount": 2, "count": 3, "flag": True, "inner": Inner(1.0)})
    assert t == Thing("a", 2.0, 3, True, None, Inner(1.0))
    assert isinstance(t.amount, float)
    assert from_dict(Thing, {"name": "a", "amount": 1, "note": None}).note is None


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ([], "must be an object"),
        ({"name": "a"}, "missing 'amount'"),
        ({"name": "a", "amount": 1, "zzz": 1}, "unknown field"),
        ({"name": 1, "amount": 1}, "Thing.name must be text"),
        ({"name": "a", "amount": "1"}, "Thing.amount must be a number"),
        ({"name": "a", "amount": True}, "must be a number"),
        ({"name": "a", "amount": 1, "count": 1.5}, "whole number"),
        ({"name": "a", "amount": 1, "flag": 1}, "true or false"),
    ],
)
def test_errors(data: object, message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        from_dict(Thing, data)


def test_non_scalar_fields_pass_through() -> None:
    @dataclass(frozen=True)
    class WithMap:
        values: dict[str, float]

    assert from_dict(WithMap, {"values": {"a": 1.0}}).values == {"a": 1.0}
