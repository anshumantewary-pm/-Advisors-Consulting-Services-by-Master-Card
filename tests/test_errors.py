import pytest

from cardwise.core.errors import CardwiseError, UnknownNameError, ValidationError


def test_hierarchy() -> None:
    assert issubclass(ValidationError, CardwiseError)
    assert issubclass(ValidationError, ValueError)
    assert issubclass(UnknownNameError, KeyError)


def test_unknown_name_prints_plainly() -> None:
    assert str(UnknownNameError("no segment 'x'")) == "no segment 'x'"
    assert str(UnknownNameError()) == "unknown name"
    with pytest.raises(CardwiseError):
        raise UnknownNameError("x")
