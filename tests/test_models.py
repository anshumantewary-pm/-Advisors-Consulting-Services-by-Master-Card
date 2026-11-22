import pytest

from cardwise.core.errors import UnknownNameError
from cardwise.whatif.models import MODELS, get_model
from cardwise.whatif.sensitivity import tornado


@pytest.mark.parametrize("name", list(MODELS))
def test_every_model_runs_on_its_defaults(name: str) -> None:
    m = get_model(name)
    assert isinstance(m.fn(dict(m.defaults)), float)


def test_card_model_tornado_ranks_inputs() -> None:
    m = get_model("card")
    t = tornado(m.fn, dict(m.defaults))
    assert t.bars[0].swing >= t.bars[-1].swing


def test_unknown_model() -> None:
    with pytest.raises(UnknownNameError, match="available"):
        get_model("nope")
