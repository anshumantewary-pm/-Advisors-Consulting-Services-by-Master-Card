"""Retention offer targeting: which at-risk customers are worth an offer?

For each segment the expected value of making an offer is
``customers x (churn probability x save rate x CLV - offer cost)``,
where the save rate is the share of would-be churners the offer keeps
(the uplift over doing nothing). Segments with negative value are left alone.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from cardwise.core.errors import ValidationError
from cardwise.core.result import Result
from cardwise.core.validate import require_fraction, require_non_negative


@dataclass(frozen=True)
class RetentionSegment(Result):
    name: str
    customers: float
    churn_probability: float
    clv: float  # value kept if the customer stays
    offer_cost: float  # per customer offered (incentive x take-up + contact)
    save_rate: float  # share of would-be churners the offer keeps


@dataclass(frozen=True)
class SegmentDecision(Result):
    name: str
    value_per_customer: float
    total_value: float
    target: bool
    break_even_save_rate: float | None


@dataclass(frozen=True)
class RetentionPlan(Result):
    decisions: tuple[SegmentDecision, ...]  # best value first
    customers_targeted: float
    budget: float
    expected_value: float  # net value of the targeted segments
    customers_saved: float


def retention_plan(segments: Sequence[RetentionSegment]) -> RetentionPlan:
    if not segments:
        raise ValidationError("give at least one segment")
    decisions = []
    targeted = budget = value = saved = 0.0
    for s in segments:
        n = require_non_negative(f"{s.name}.customers", s.customers)
        p = require_fraction(f"{s.name}.churn_probability", s.churn_probability)
        clv = require_non_negative(f"{s.name}.clv", s.clv)
        cost = require_non_negative(f"{s.name}.offer_cost", s.offer_cost)
        save = require_fraction(f"{s.name}.save_rate", s.save_rate)
        per = p * save * clv - cost
        target = per > 0
        be = cost / (p * clv) if p * clv > 0 else None
        if be is not None and be > 1:
            be = None  # no save rate can make this offer pay
        decisions.append(SegmentDecision(s.name, per, per * n, target, be))
        if target:
            targeted += n
            budget += n * cost
            value += n * per
            saved += n * p * save
    decisions.sort(key=lambda d: -d.value_per_customer)
    return RetentionPlan(tuple(decisions), targeted, budget, value, saved)
