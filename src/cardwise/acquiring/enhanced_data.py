"""Enhanced data (Level 2/3) savings on commercial card acceptance.

Business-to-business merchants that pass line-item data with commercial card
transactions can qualify for lower interchange categories. Rates vary by
network, region and card type, so they are inputs here, not built-in values.
"""

from __future__ import annotations

from dataclasses import dataclass

from cardwise.core.errors import ValidationError
from cardwise.core.result import Result
from cardwise.core.validate import require_fraction, require_non_negative


@dataclass(frozen=True)
class EnhancedDataSavings(Result):
    commercial_volume: float
    cost_today: float
    cost_after: float
    annual_saving: float
    effective_rate_today: float
    effective_rate_after: float
    payback_months: float | None  # implementation cost / monthly saving


def enhanced_data_savings(
    commercial_volume: float,
    standard_rate: float,
    level2_rate: float,
    level3_rate: float,
    share_level2_today: float,
    share_level3_today: float,
    share_level2_after: float,
    share_level3_after: float,
    implementation_cost: float = 0.0,
) -> EnhancedDataSavings:
    vol = require_non_negative("commercial_volume", commercial_volume)
    rates = {}
    for name, value in (
        ("standard_rate", standard_rate),
        ("level2_rate", level2_rate),
        ("level3_rate", level3_rate),
    ):
        rates[name] = require_fraction(name, value)
    shares = {}
    for name, value in (
        ("share_level2_today", share_level2_today),
        ("share_level3_today", share_level3_today),
        ("share_level2_after", share_level2_after),
        ("share_level3_after", share_level3_after),
    ):
        shares[name] = require_fraction(name, value)
    for when in ("today", "after"):
        if shares[f"share_level2_{when}"] + shares[f"share_level3_{when}"] > 1 + 1e-9:
            raise ValidationError(f"level 2 and level 3 shares {when} add up to more than 1")
    cost_impl = require_non_negative("implementation_cost", implementation_cost)

    def blended(l2: float, l3: float) -> float:
        std = 1 - l2 - l3
        return std * rates["standard_rate"] + l2 * rates["level2_rate"] + l3 * rates["level3_rate"]

    today = blended(shares["share_level2_today"], shares["share_level3_today"])
    after = blended(shares["share_level2_after"], shares["share_level3_after"])
    saving = vol * (today - after)
    payback = cost_impl / (saving / 12) if saving > 0 else None
    return EnhancedDataSavings(vol, vol * today, vol * after, saving, today, after, payback)
