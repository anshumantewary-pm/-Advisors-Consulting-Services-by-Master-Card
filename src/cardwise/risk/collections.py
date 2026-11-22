"""Early-stage collections economics: what a better cure rate is worth.

Balances that enter early delinquency either cure (return to current) or go
on to charge off with some probability. A collections strategy (digital
reminders, self-cure journeys, earlier calls, hardship plans) raises the cure
rate at a cost per account worked.
"""

from __future__ import annotations

from dataclasses import dataclass

from cardwise.core.errors import ValidationError
from cardwise.core.result import Result
from cardwise.core.validate import require_fraction, require_non_negative


@dataclass(frozen=True)
class CollectionsStrategy(Result):
    entering_balances: float  # balances entering early delinquency per year
    losses_before: float
    losses_after: float
    losses_avoided: float
    strategy_cost: float
    net_benefit: float
    roi: float | None
    break_even_cure_uplift: float | None  # extra cure rate (points) that pays for the strategy


def collections_strategy(
    entering_balances: float,
    accounts: float,
    baseline_cure_rate: float,
    new_cure_rate: float,
    loss_given_no_cure: float,
    cost_per_account: float,
) -> CollectionsStrategy:
    """``loss_given_no_cure``: share of an uncured balance eventually charged off."""
    bal = require_non_negative("entering_balances", entering_balances)
    n = require_non_negative("accounts", accounts)
    before = require_fraction("baseline_cure_rate", baseline_cure_rate)
    after = require_fraction("new_cure_rate", new_cure_rate)
    if after < before:
        raise ValidationError("new_cure_rate is below baseline_cure_rate")
    loss = require_fraction("loss_given_no_cure", loss_given_no_cure)
    cost_each = require_non_negative("cost_per_account", cost_per_account)
    losses_before = bal * (1 - before) * loss
    losses_after = bal * (1 - after) * loss
    avoided = losses_before - losses_after
    cost = n * cost_each
    break_even = cost / (bal * loss) if bal * loss > 0 else None
    return CollectionsStrategy(
        entering_balances=bal,
        losses_before=losses_before,
        losses_after=losses_after,
        losses_avoided=avoided,
        strategy_cost=cost,
        net_benefit=avoided - cost,
        roi=(avoided - cost) / cost if cost else None,
        break_even_cure_uplift=break_even,
    )
