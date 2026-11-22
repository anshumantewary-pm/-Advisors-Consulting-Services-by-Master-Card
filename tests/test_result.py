from dataclasses import dataclass

from cardwise.core.result import Result, Step


@dataclass(frozen=True)
class Demo(Result):
    a: float
    steps: tuple[Step, ...]


def test_to_dict_is_recursive() -> None:
    d = Demo(1.0, (Step("x", 2.0, "$"),)).to_dict()
    assert d == {"a": 1.0, "steps": ({"label": "x", "value": 2.0, "unit": "$"},)}
