"""Card portfolio health: activity, spend, balances and revolve behaviour."""

from __future__ import annotations

from dataclasses import dataclass

from cardwise.core.errors import ValidationError
from cardwise.core.result import Result
from cardwise.core.validate import require_non_negative, require_positive


@dataclass(frozen=True)
class PortfolioKPIs(Result):
    accounts: float
    active_accounts: float
    active_rate: float  # active / open accounts
    purchase_volume: float
    spend_per_active: float
    receivables: float
    balance_per_active: float
    revolving_balances: float
    revolve_rate: float  # share of receivables that pays interest
    transactions: float | None
    average_ticket: float | None
    transactions_per_active: float | None


def portfolio_kpis(
    accounts: float,
    active_accounts: float,
    purchase_volume: float,
    receivables: float,
    revolving_balances: float,
    transactions: float | None = None,
) -> PortfolioKPIs:
    """Headline KPIs for one period (usually a year) of a card portfolio."""
    accounts = require_positive("accounts", accounts)
    active = require_non_negative("active_accounts", active_accounts)
    volume = require_non_negative("purchase_volume", purchase_volume)
    receivables = require_non_negative("receivables", receivables)
    revolving = require_non_negative("revolving_balances", revolving_balances)
    if active > accounts:
        raise ValidationError("active_accounts cannot exceed accounts")
    if revolving > receivables:
        raise ValidationError("revolving_balances cannot exceed receivables")
    txns = None if transactions is None else require_non_negative("transactions", transactions)
    return PortfolioKPIs(
        accounts=accounts,
        active_accounts=active,
        active_rate=active / accounts,
        purchase_volume=volume,
        spend_per_active=volume / active if active else 0.0,
        receivables=receivables,
        balance_per_active=receivables / active if active else 0.0,
        revolving_balances=revolving,
        revolve_rate=revolving / receivables if receivables else 0.0,
        transactions=txns,
        average_ticket=(volume / txns) if txns else None,
        transactions_per_active=(txns / active) if txns is not None and active else None,
    )
