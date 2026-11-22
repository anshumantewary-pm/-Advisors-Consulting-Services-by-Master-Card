"""Credit line increase economics: extra balances and spend against extra losses.

A line increase earns interest on the new balances customers draw and
interchange on extra spend, and costs funding on those balances, losses on
them, and a small rise in the loss rate on the balances customers already had
(more headroom lets a deteriorating customer go further before stopping).
"""

from __future__ import annotations

from dataclasses import dataclass

from cardwise.core.result import Result, Step
from cardwise.core.validate import require_fraction, require_non_negative


@dataclass(frozen=True)
class LineIncrease(Result):
    accounts: float
    new_limit: float  # total extra credit extended
    new_balances: float
    new_revolving: float
    interest: float
    interchange: float
    funding_cost: float
    new_balance_losses: float
    existing_balance_losses: float
    net_profit: float
    profit_per_account: float
    break_even_loss_rate: float | None  # loss rate on new balances that zeroes the profit
    steps: tuple[Step, ...]


def line_increase(
    accounts: float,
    increase_per_account: float,
    utilisation: float,
    revolve_share: float,
    apr: float,
    cost_of_funds: float,
    loss_rate: float,
    existing_balance_per_account: float = 0.0,
    loss_rate_uplift_on_existing: float = 0.0,
    extra_spend_per_account: float = 0.0,
    interchange_rate: float = 0.0,
) -> LineIncrease:
    """Annual profit of offering ``increase_per_account`` to ``accounts`` customers."""
    n = require_non_negative("accounts", accounts)
    inc = require_non_negative("increase_per_account", increase_per_account)
    util = require_fraction("utilisation", utilisation)
    revolve = require_fraction("revolve_share", revolve_share)
    for name, value in (
        ("apr", apr),
        ("cost_of_funds", cost_of_funds),
        ("loss_rate", loss_rate),
        ("loss_rate_uplift_on_existing", loss_rate_uplift_on_existing),
        ("interchange_rate", interchange_rate),
    ):
        require_fraction(name, value)
    existing = require_non_negative("existing_balance_per_account", existing_balance_per_account)
    spend = require_non_negative("extra_spend_per_account", extra_spend_per_account)
    new_balances = n * inc * util
    new_revolving = new_balances * revolve
    interest = new_revolving * apr
    interchange = n * spend * interchange_rate
    funding = new_balances * cost_of_funds
    new_losses = new_balances * loss_rate
    old_losses = n * existing * loss_rate_uplift_on_existing
    profit = interest + interchange - funding - new_losses - old_losses
    margin_before_losses = interest + interchange - funding - old_losses
    break_even = margin_before_losses / new_balances if new_balances else None
    steps = (
        Step("Interest on new revolving balances", interest, "$"),
        Step("Interchange on extra spend", interchange, "$"),
        Step("Funding cost of new balances", -funding, "$"),
        Step("Losses on new balances", -new_losses, "$"),
        Step("Extra losses on existing balances", -old_losses, "$"),
        Step("Net annual profit", profit, "$"),
    )
    return LineIncrease(
        accounts=n,
        new_limit=n * inc,
        new_balances=new_balances,
        new_revolving=new_revolving,
        interest=interest,
        interchange=interchange,
        funding_cost=funding,
        new_balance_losses=new_losses,
        existing_balance_losses=old_losses,
        net_profit=profit,
        profit_per_account=profit / n if n else 0.0,
        break_even_loss_rate=break_even,
        steps=steps,
    )
