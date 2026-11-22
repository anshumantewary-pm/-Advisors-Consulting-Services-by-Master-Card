"""Merchant pricing: what a merchant pays, what the acquirer keeps.

The merchant discount rate (MDR) splits into interchange (to the issuer),
scheme fees (to the network) and the acquirer's margin. ``compare_pricing``
contrasts a blended rate with interchange-plus-plus (IC++) for the same
card mix, which is the core of most merchant pricing reviews.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from cardwise.core.errors import ValidationError
from cardwise.core.result import Result
from cardwise.core.validate import require_fraction, require_non_empty, require_non_negative


@dataclass(frozen=True)
class CardMix(Result):
    """One slice of a merchant's volume: card type, share of volume, interchange rate."""

    card_type: str
    share: float
    interchange_rate: float


def blended_interchange(mix: Sequence[CardMix]) -> float:
    """Volume-weighted interchange rate. Shares must add up to 1."""
    require_non_empty("mix", mix)
    for m in mix:
        require_fraction(f"{m.card_type}.share", m.share)
        require_fraction(f"{m.card_type}.interchange_rate", m.interchange_rate)
    total = sum(m.share for m in mix)
    if abs(total - 1) > 1e-6:
        raise ValidationError(f"card mix shares must add up to 1, got {total:.4f}")
    return sum(m.share * m.interchange_rate for m in mix)


@dataclass(frozen=True)
class MDRSplit(Result):
    volume: float
    mdr: float
    merchant_cost: float
    interchange: float
    scheme_fees: float
    acquirer_margin: float
    acquirer_margin_rate: float


def mdr_split(
    volume: float, mdr: float, interchange_rate: float, scheme_fee_rate: float
) -> MDRSplit:
    """Who gets what from one merchant's fees. The parts add up to the merchant's cost."""
    volume = require_non_negative("volume", volume)
    for name, value in (
        ("mdr", mdr),
        ("interchange_rate", interchange_rate),
        ("scheme_fee_rate", scheme_fee_rate),
    ):
        require_fraction(name, value)
    margin_rate = mdr - interchange_rate - scheme_fee_rate
    return MDRSplit(
        volume=volume,
        mdr=mdr,
        merchant_cost=volume * mdr,
        interchange=volume * interchange_rate,
        scheme_fees=volume * scheme_fee_rate,
        acquirer_margin=volume * margin_rate,
        acquirer_margin_rate=margin_rate,
    )


@dataclass(frozen=True)
class PricingComparison(Result):
    blended_interchange: float
    blended: MDRSplit
    ic_plus_plus: MDRSplit
    merchant_saving: float  # blended cost - IC++ cost (positive: IC++ is cheaper)
    equivalent_markup: float  # IC++ markup that would give the acquirer the same margin


def compare_pricing(
    volume: float,
    mix: Sequence[CardMix],
    scheme_fee_rate: float,
    blended_mdr: float,
    markup_rate: float,
) -> PricingComparison:
    """Blended MDR vs IC++ (pass-through interchange and scheme fees plus a markup)."""
    ic = blended_interchange(mix)
    require_fraction("markup_rate", markup_rate)
    blended = mdr_split(volume, blended_mdr, ic, scheme_fee_rate)
    icpp = mdr_split(volume, ic + scheme_fee_rate + markup_rate, ic, scheme_fee_rate)
    return PricingComparison(
        blended_interchange=ic,
        blended=blended,
        ic_plus_plus=icpp,
        merchant_saving=blended.merchant_cost - icpp.merchant_cost,
        equivalent_markup=blended.acquirer_margin_rate,
    )
