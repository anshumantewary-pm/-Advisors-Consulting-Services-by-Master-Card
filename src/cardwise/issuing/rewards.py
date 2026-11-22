"""Rewards programme economics: what a point really costs and whether a programme pays."""

from __future__ import annotations

from dataclasses import dataclass

from cardwise.core.result import Result
from cardwise.core.validate import require_fraction, require_non_negative, require_positive


@dataclass(frozen=True)
class RewardsEconomics(Result):
    effective_rewards_rate: float  # cost of rewards as a share of spend
    cost_per_point: float  # after breakage
    participants: float
    baseline_spend: float
    incremental_spend: float
    incremental_margin: float  # extra interchange (net of network fees) from the lift
    programme_cost: float  # rewards on all spend plus fixed cost
    net_benefit: float
    roi: float | None  # net benefit / programme cost
    break_even_lift: float | None  # spend lift that makes net benefit zero


def effective_rewards_rate(points_per_unit: float, point_value: float, breakage: float) -> float:
    """Rewards cost per unit of spend: earn rate x point value x share redeemed."""
    require_non_negative("points_per_unit", points_per_unit)
    require_non_negative("point_value", point_value)
    require_fraction("breakage", breakage)
    return points_per_unit * point_value * (1 - breakage)


def rewards_programme(
    participants: float,
    spend_per_participant: float,
    spend_lift: float,
    points_per_unit: float,
    point_value: float,
    breakage: float,
    interchange_rate: float,
    network_fee_rate: float = 0.0,
    fixed_cost: float = 0.0,
) -> RewardsEconomics:
    """Does a rewards programme earn back its cost through extra spend?

    Rewards are paid on all spend (baseline plus lift); only the lift earns
    *new* interchange. The break-even lift solves
    ``baseline * lift * margin = rate * baseline * (1 + lift) + fixed``.
    """
    participants = require_non_negative("participants", participants)
    spend = require_non_negative("spend_per_participant", spend_per_participant)
    lift = require_non_negative("spend_lift", spend_lift)
    require_fraction("interchange_rate", interchange_rate)
    require_fraction("network_fee_rate", network_fee_rate)
    require_non_negative("fixed_cost", fixed_cost)
    rate = effective_rewards_rate(points_per_unit, point_value, breakage)
    margin = interchange_rate - network_fee_rate
    baseline = participants * spend
    incremental = baseline * lift
    inc_margin = incremental * margin
    cost = rate * (baseline + incremental) + fixed_cost
    net = inc_margin - cost
    gap = margin - rate
    break_even = None
    if baseline > 0 and gap > 0:
        break_even = (rate * baseline + fixed_cost) / (baseline * gap)
    return RewardsEconomics(
        effective_rewards_rate=rate,
        cost_per_point=point_value * (1 - breakage),
        participants=participants,
        baseline_spend=baseline,
        incremental_spend=incremental,
        incremental_margin=inc_margin,
        programme_cost=cost,
        net_benefit=net,
        roi=net / cost if cost > 0 else None,
        break_even_lift=break_even,
    )


def points_liability(points_outstanding: float, point_value: float, breakage: float) -> float:
    """Balance-sheet liability for unredeemed points (expected redemptions x value)."""
    require_positive("point_value", point_value)
    require_non_negative("points_outstanding", points_outstanding)
    require_fraction("breakage", breakage)
    return points_outstanding * point_value * (1 - breakage)
