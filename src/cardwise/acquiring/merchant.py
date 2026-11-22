"""Merchant performance KPIs: authorisation, ticket size and chargeback standing.

Chargeback thresholds differ by network and change over time, so they are
inputs with indicative defaults, not hard-coded rules.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from cardwise.core.errors import ValidationError
from cardwise.core.result import Result
from cardwise.core.validate import require_fraction, require_non_negative, require_positive


@dataclass(frozen=True)
class ChargebackThresholds(Result):
    """Chargeback ratio (count of chargebacks / count of sales) bands. Indicative defaults."""

    early_warning: float = 0.0065
    standard: float = 0.009
    excessive: float = 0.015


@dataclass(frozen=True)
class MerchantKPIs(Result):
    attempts: float
    approvals: float
    approval_rate: float
    decline_mix: dict[str, float]  # share of declines by reason
    sales_value: float
    average_ticket: float
    chargebacks: float
    chargeback_ratio: float  # by count
    chargeback_value_ratio: float | None  # by value
    chargeback_status: str  # "healthy", "early warning", "standard program", "excessive"
    lost_sales_value: float  # declines x average ticket


def chargeback_status(ratio: float, t: ChargebackThresholds | None = None) -> str:
    t = t or ChargebackThresholds()
    if not t.early_warning <= t.standard <= t.excessive:
        raise ValidationError("chargeback thresholds must increase: early <= standard <= excessive")
    if ratio >= t.excessive:
        return "excessive"
    if ratio >= t.standard:
        return "standard program"
    if ratio >= t.early_warning:
        return "early warning"
    return "healthy"


def merchant_kpis(
    attempts: float,
    approvals: float,
    sales_value: float,
    chargebacks: float,
    chargeback_value: float | None = None,
    declines_by_reason: Mapping[str, float] | None = None,
    thresholds: ChargebackThresholds | None = None,
) -> MerchantKPIs:
    attempts = require_positive("attempts", attempts)
    approvals = require_non_negative("approvals", approvals)
    if approvals > attempts:
        raise ValidationError("approvals cannot exceed attempts")
    value = require_non_negative("sales_value", sales_value)
    cbs = require_non_negative("chargebacks", chargebacks)
    declines = attempts - approvals
    reasons = dict(declines_by_reason or {})
    for k, v in reasons.items():
        require_non_negative(f"declines_by_reason.{k}", v)
    total_reasons = sum(reasons.values())
    if total_reasons > declines + 1e-9:
        raise ValidationError("declines_by_reason add up to more than the declines")
    ticket = value / approvals if approvals else 0.0
    ratio = cbs / approvals if approvals else 0.0
    value_ratio = None
    if chargeback_value is not None:
        cv = require_non_negative("chargeback_value", chargeback_value)
        value_ratio = cv / value if value else 0.0
    return MerchantKPIs(
        attempts=attempts,
        approvals=approvals,
        approval_rate=approvals / attempts,
        decline_mix={k: v / declines for k, v in reasons.items()} if declines else {},
        sales_value=value,
        average_ticket=ticket,
        chargebacks=cbs,
        chargeback_ratio=ratio,
        chargeback_value_ratio=value_ratio,
        chargeback_status=chargeback_status(ratio, thresholds),
        lost_sales_value=declines * ticket,
    )


def approval_uplift_value(
    attempts: float, approval_rate: float, target_rate: float, average_ticket: float, margin: float
) -> float:
    """Extra margin from lifting the approval rate (e.g. via tokenisation or retries)."""
    require_non_negative("attempts", attempts)
    require_fraction("approval_rate", approval_rate)
    require_fraction("target_rate", target_rate)
    require_non_negative("average_ticket", average_ticket)
    require_fraction("margin", margin)
    return attempts * max(target_rate - approval_rate, 0.0) * average_ticket * margin
