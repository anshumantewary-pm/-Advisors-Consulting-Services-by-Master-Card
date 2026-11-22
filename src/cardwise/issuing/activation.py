"""Activation campaign economics: is it worth paying to wake dormant cards?

Only incremental activations count: the response in the targeted group minus
the response a control group would have shown anyway. Each new active earns a
yearly profit that decays with retention, discounted to today.
"""

from __future__ import annotations

from dataclasses import dataclass

from cardwise.core.errors import ValidationError
from cardwise.core.result import Result
from cardwise.core.validate import (
    require_count,
    require_fraction,
    require_non_negative,
    require_rate,
)


@dataclass(frozen=True)
class ActivationCampaign(Result):
    targeted: float
    incremental_activations: float
    campaign_cost: float  # contact cost for everyone + incentive for every responder
    cost_per_incremental: float | None
    value_per_active: float  # discounted profit of one new active over the horizon
    value_created: float
    net_value: float
    roi: float | None
    payback_years: float | None  # first year cumulative discounted profit covers the cost


def activation_campaign(
    targeted: float,
    response_rate: float,
    control_rate: float,
    contact_cost: float,
    incentive: float,
    annual_profit_per_active: float,
    retention: float,
    discount_rate: float = 0.10,
    years: int = 3,
) -> ActivationCampaign:
    n = require_non_negative("targeted", targeted)
    resp = require_fraction("response_rate", response_rate)
    ctrl = require_fraction("control_rate", control_rate)
    if ctrl > resp:
        raise ValidationError("control_rate is above response_rate: the campaign adds nothing")
    contact = require_non_negative("contact_cost", contact_cost)
    reward = require_non_negative("incentive", incentive)
    profit = require_non_negative("annual_profit_per_active", annual_profit_per_active)
    keep = require_fraction("retention", retention)
    d = require_rate("discount_rate", discount_rate)
    horizon = require_count("years", years)
    incremental = n * (resp - ctrl)
    # Incentives go to every responder, including those who would have activated anyway.
    cost = n * contact + n * resp * reward
    yearly = [profit * keep**t / (1 + d) ** (t + 1) for t in range(horizon)]
    value_per_active = sum(yearly)
    created = incremental * value_per_active
    payback = None
    cumulative = 0.0
    for t, v in enumerate(yearly, start=1):
        cumulative += incremental * v
        if cumulative >= cost:
            payback = float(t)
            break
    return ActivationCampaign(
        targeted=n,
        incremental_activations=incremental,
        campaign_cost=cost,
        cost_per_incremental=cost / incremental if incremental else None,
        value_per_active=value_per_active,
        value_created=created,
        net_value=created - cost,
        roi=(created - cost) / cost if cost else None,
        payback_years=payback,
    )
