import pytest

from cardwise.acquiring.pricing import CardMix, blended_interchange, compare_pricing, mdr_split
from cardwise.core.errors import ValidationError

MIX = [
    CardMix("consumer debit", 0.5, 0.002),
    CardMix("consumer credit", 0.3, 0.003),
    CardMix("commercial", 0.2, 0.015),
]


def test_blended_interchange() -> None:
    assert blended_interchange(MIX) == pytest.approx(0.0049)


def test_mdr_split_adds_up() -> None:
    s = mdr_split(10e6, 0.015, 0.0049, 0.0015)
    assert s.interchange + s.scheme_fees + s.acquirer_margin == pytest.approx(s.merchant_cost)
    assert s.acquirer_margin_rate == pytest.approx(0.0086)


def test_compare_pricing() -> None:
    c = compare_pricing(10e6, MIX, 0.0015, 0.015, 0.003)
    assert c.ic_plus_plus.mdr == pytest.approx(0.0049 + 0.0015 + 0.003)
    assert c.merchant_saving == pytest.approx(10e6 * (0.015 - 0.0094))
    assert c.equivalent_markup == pytest.approx(0.0086)


@pytest.mark.parametrize(
    ("mix", "message"),
    [
        ([], "mix"),
        ([CardMix("a", 0.5, 0.01)], "add up to 1"),
        ([CardMix("a", 1.0, 2.0)], "a.interchange_rate"),
    ],
)
def test_bad_mix(mix: list[CardMix], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        blended_interchange(mix)
