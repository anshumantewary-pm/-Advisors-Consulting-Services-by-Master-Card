"""Credit card P&L: from volumes and rates to profit per account and ROA.

Every line is volume x rate, so a consultant can trace each figure and the
lines always add up: revenue - funding - rewards - losses - network fees - opex
equals pre-tax profit (asserted in the tests).
"""

from __future__ import annotations

from dataclasses import dataclass

from cardwise.core.result import Result, Step
from cardwise.core.validate import require_fraction, require_non_negative, require_positive


@dataclass(frozen=True)
class CardEconomics(Result):
    """Annual rates and volumes for a card portfolio."""

    active_accounts: float
    purchase_volume: float
    receivables: float  # average balances
    revolving_balances: float  # average interest-bearing balances
    interchange_rate: float = 0.018  # issuer interchange as a share of volume
    apr: float = 0.20  # yield on revolving balances
    fee_income: float = 0.0  # annual, late, FX and other fees in total
    cost_of_funds: float = 0.045
    rewards_rate: float = 0.008  # rewards cost as a share of volume
    net_credit_loss_rate: float = 0.035  # net charge-offs as a share of receivables
    network_fee_rate: float = 0.0012  # scheme and processing fees as a share of volume
    cost_per_account: float = 60.0  # servicing, statements, collections, IT


@dataclass(frozen=True)
class CardPnL(Result):
    interchange: float
    interest: float
    fees: float
    revenue: float
    funding_cost: float
    rewards_cost: float
    credit_losses: float
    network_fees: float
    operating_cost: float
    risk_adjusted_revenue: float  # revenue - funding - losses
    pre_tax_profit: float
    profit_per_active: float
    roa: float  # pre-tax profit / receivables
    revenue_mix: dict[str, float]
    steps: tuple[Step, ...]


def card_pnl(e: CardEconomics) -> CardPnL:
    active = require_positive("active_accounts", e.active_accounts)
    volume = require_non_negative("purchase_volume", e.purchase_volume)
    receivables = require_positive("receivables", e.receivables)
    revolving = require_non_negative("revolving_balances", e.revolving_balances)
    for name in ("interchange_rate", "apr", "cost_of_funds", "rewards_rate",
                 "net_credit_loss_rate", "network_fee_rate"):  # fmt: skip
        require_fraction(name, getattr(e, name))
    require_non_negative("fee_income", e.fee_income)
    require_non_negative("cost_per_account", e.cost_per_account)

    interchange = volume * e.interchange_rate
    interest = revolving * e.apr
    fees = e.fee_income
    revenue = interchange + interest + fees
    funding = receivables * e.cost_of_funds
    rewards = volume * e.rewards_rate
    losses = receivables * e.net_credit_loss_rate
    network = volume * e.network_fee_rate
    opex = active * e.cost_per_account
    profit = revenue - funding - rewards - losses - network - opex
    steps = (
        Step("Interchange income", interchange, "$"),
        Step("Interest income", interest, "$"),
        Step("Fee income", fees, "$"),
        Step("Revenue", revenue, "$"),
        Step("Funding cost", -funding, "$"),
        Step("Rewards cost", -rewards, "$"),
        Step("Net credit losses", -losses, "$"),
        Step("Network and processing fees", -network, "$"),
        Step("Operating cost", -opex, "$"),
        Step("Pre-tax profit", profit, "$"),
    )
    mix = {"interchange": interchange, "interest": interest, "fees": fees}
    return CardPnL(
        interchange=interchange,
        interest=interest,
        fees=fees,
        revenue=revenue,
        funding_cost=funding,
        rewards_cost=rewards,
        credit_losses=losses,
        network_fees=network,
        operating_cost=opex,
        risk_adjusted_revenue=revenue - funding - losses,
        pre_tax_profit=profit,
        profit_per_active=profit / active,
        roa=profit / receivables,
        revenue_mix={k: (v / revenue if revenue else 0.0) for k, v in mix.items()},
        steps=steps,
    )
