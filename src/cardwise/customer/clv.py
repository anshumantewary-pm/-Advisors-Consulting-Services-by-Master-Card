"""Customer lifetime value with retention and discounting."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from cardwise.core.result import Result
from cardwise.core.validate import require_fraction, require_non_negative, require_rate


@dataclass(frozen=True)
class CLV(Result):
    annual_margin: float
    retention: float
    discount_rate: float
    expected_lifetime_years: float  # 1 / (1 - retention)
    clv: float  # present value of margin, first year received at year end
    max_acquisition_cost: float  # CLV / target LTV:CAC ratio


def lifetime_value(
    annual_margin: float, retention: float, discount_rate: float, target_ltv_to_cac: float = 3.0
) -> CLV:
    """Margin x r-adjusted annuity: ``m / (1 + d - r)`` for constant retention ``r``.

    Margin arrives at the end of year one, then each later year with probability
    ``r`` of the customer still being active.
    """
    margin = require_non_negative("annual_margin", annual_margin)
    r = require_fraction("retention", retention)
    d = require_rate("discount_rate", discount_rate)
    ratio = require_non_negative("target_ltv_to_cac", target_ltv_to_cac)
    if r >= 1:
        lifetime = float("inf")
        clv = margin / d if d > 0 else float("inf")
    else:
        lifetime = 1 / (1 - r)
        clv = margin / (1 + d - r)
    return CLV(margin, r, d, lifetime, clv, clv / ratio if ratio else float("inf"))


def segment_values(
    segments: Mapping[str, tuple[float, float, float]], discount_rate: float
) -> dict[str, CLV]:
    """CLV per segment from ``{name: (customers, annual_margin, retention)}``; adds a total."""
    out = {}
    for name, (count, margin, retention) in segments.items():
        require_non_negative(f"{name}.customers", count)
        out[name] = lifetime_value(margin, retention, discount_rate)
    return out


def portfolio_value(segments: Mapping[str, tuple[float, float, float]], discount_rate: float) -> float:
    """Total customer equity: sum of customers x CLV over segments."""
    values = segment_values(segments, discount_rate)
    return sum(segments[n][0] * v.clv for n, v in values.items())
