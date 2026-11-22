"""Indicative KPI ranges by card portfolio type.

These are screening rules of thumb drawn from typical published industry
ratios, not market data for a specific market, issuer or date. Replace them
with a client's peer data (``peers.scorecard``) when you have it.
"""

from __future__ import annotations

from dataclasses import dataclass

from cardwise.core.errors import UnknownNameError
from cardwise.core.result import Result

Range = tuple[float, float]


@dataclass(frozen=True)
class KPIRange(Result):
    key: str
    label: str
    low: float
    high: float
    higher_is_better: bool
    unit: str = "%"  # "%" for fractions, "bp" for basis points

    def status(self, value: float) -> str:
        """ "below", "within" or "above" the range."""
        if value < self.low:
            return "below"
        if value > self.high:
            return "above"
        return "within"

    def is_weak(self, value: float) -> bool:
        s = self.status(value)
        return (s == "below") if self.higher_is_better else (s == "above")


@dataclass(frozen=True)
class PortfolioType(Result):
    key: str
    name: str
    ranges: tuple[KPIRange, ...]

    def get(self, key: str) -> KPIRange | None:
        return next((r for r in self.ranges if r.key == key), None)


def _r(key: str, label: str, low: float, high: float, hib: bool, unit: str = "%") -> KPIRange:
    return KPIRange(key, label, low, high, hib, unit)


PORTFOLIO_TYPES: dict[str, PortfolioType] = {
    t.key: t
    for t in (
        PortfolioType(
            "mass_credit",
            "Mass-market credit card",
            (
                _r("active_rate", "Active rate", 0.55, 0.75, True),
                _r("revolve_rate", "Revolve rate", 0.45, 0.70, True),
                _r("net_credit_loss_rate", "Net credit loss rate", 0.025, 0.05, False),
                _r("rewards_rate", "Rewards cost / spend", 0.003, 0.008, False),
                _r("roa", "Pre-tax ROA", 0.025, 0.05, True),
                _r("approval_rate", "Authorisation approval rate", 0.85, 0.93, True),
                _r("fraud_bps", "Fraud losses (bp of spend)", 3, 8, False, "bp"),
            ),
        ),
        PortfolioType(
            "premium_credit",
            "Premium / rewards credit card",
            (
                _r("active_rate", "Active rate", 0.70, 0.88, True),
                _r("revolve_rate", "Revolve rate", 0.20, 0.45, True),
                _r("net_credit_loss_rate", "Net credit loss rate", 0.01, 0.03, False),
                _r("rewards_rate", "Rewards cost / spend", 0.008, 0.015, False),
                _r("roa", "Pre-tax ROA", 0.015, 0.04, True),
                _r("approval_rate", "Authorisation approval rate", 0.88, 0.95, True),
                _r("fraud_bps", "Fraud losses (bp of spend)", 4, 10, False, "bp"),
            ),
        ),
        PortfolioType(
            "commercial",
            "Commercial / SME card",
            (
                _r("active_rate", "Active rate", 0.60, 0.85, True),
                _r("revolve_rate", "Revolve rate", 0.05, 0.25, True),
                _r("net_credit_loss_rate", "Net credit loss rate", 0.005, 0.02, False),
                _r("rewards_rate", "Rewards cost / spend", 0.004, 0.010, False),
                _r("roa", "Pre-tax ROA", 0.02, 0.06, True),
                _r("approval_rate", "Authorisation approval rate", 0.88, 0.95, True),
                _r("fraud_bps", "Fraud losses (bp of spend)", 2, 6, False, "bp"),
            ),
        ),
        PortfolioType(
            "debit",
            "Consumer debit card",
            (
                _r("active_rate", "Active rate", 0.65, 0.85, True),
                _r("approval_rate", "Authorisation approval rate", 0.88, 0.96, True),
                _r("fraud_bps", "Fraud losses (bp of spend)", 1, 5, False, "bp"),
                _r("rewards_rate", "Rewards cost / spend", 0.0, 0.002, False),
            ),
        ),
    )
}


def get_portfolio_type(key: str) -> PortfolioType:
    try:
        return PORTFOLIO_TYPES[key]
    except KeyError:
        known = ", ".join(PORTFOLIO_TYPES)
        raise UnknownNameError(f"unknown portfolio type {key!r}; choose one of: {known}") from None
