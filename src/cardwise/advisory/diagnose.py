"""Portfolio diagnosis: KPIs vs indicative ranges, each gap sized in money.

``diagnose(review)`` computes the portfolio KPIs and card P&L, checks every
KPI against the portfolio type's range, and turns each weak KPI into an
opportunity with an estimated annual profit impact of closing the gap to the
edge of the range, plus the levers a consulting team would pull. Opportunities
are ranked by value so the report leads with what matters most.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from cardwise.benchmark.ranges import KPIRange, PortfolioType, get_portfolio_type
from cardwise.core.result import Result
from cardwise.core.validate import require_fraction, require_non_negative
from cardwise.issuing.pnl import CardEconomics, CardPnL, card_pnl
from cardwise.issuing.portfolio import PortfolioKPIs, portfolio_kpis


@dataclass(frozen=True)
class PortfolioReview(Result):
    """Everything a first-pass portfolio review needs, for one year."""

    name: str
    portfolio_type: str
    accounts: float
    economics: CardEconomics
    transactions: float | None = None
    approval_rate: float | None = None
    fraud_losses: float | None = None
    currency: str = "$"


@dataclass(frozen=True)
class Check(Result):
    key: str
    label: str
    value: float
    low: float
    high: float
    unit: str
    status: str  # below / within / above
    weak: bool


@dataclass(frozen=True)
class Opportunity(Result):
    key: str
    title: str
    detail: str
    annual_value: float  # estimated pre-tax profit uplift of reaching the range edge
    levers: tuple[str, ...]


@dataclass(frozen=True)
class Diagnosis(Result):
    review: PortfolioReview
    portfolio_type: PortfolioType
    kpis: PortfolioKPIs
    pnl: CardPnL
    checks: tuple[Check, ...]
    opportunities: tuple[Opportunity, ...]
    total_opportunity: float
    health_score: int  # share of checked KPIs not weak, 0-100
    strengths: tuple[str, ...] = field(default=())


# KPIs that are results of the others (sizing them too would double-count).
OUTCOMES = frozenset({"roa"})

LEVERS: dict[str, tuple[str, ...]] = {
    "active_rate": (
        "Early-life activation journey: first-purchase incentive within 30 days",
        "Re-activation offers for dormant accounts, targeted by propensity model",
        "Push provisioning to mobile wallets and card-on-file at top merchants",
    ),
    "revolve_rate": (
        "Balance-transfer and instalment offers to engaged transactors",
        "Risk-based APR pricing reviewed by segment",
        "Credit line increases for low-risk, high-utilisation customers",
    ),
    "net_credit_loss_rate": (
        "Tighten acquisition cut-offs on the worst-performing vintages",
        "Early-stage collections: digital reminders and self-cure journeys",
        "Line management: proactive decreases for deteriorating behaviour scores",
    ),
    "rewards_rate": (
        "Rebase earn rates on low-margin categories; cap bonus categories",
        "Shift rewards toward lower-cost partner-funded offers",
        "Increase breakage-neutral redemption options with better unit cost",
    ),
    "approval_rate": (
        "Network tokenisation and account updater for card-on-file payments",
        "Smart retries and issuer decline-code analysis with top merchants",
        "Recalibrate fraud rules causing false declines",
    ),
    "fraud_bps": (
        "Adopt machine-learning transaction scoring with cost-based thresholds",
        "3-D Secure risk-based authentication for e-commerce",
        "Consortium fraud data and mule-account detection",
    ),
}


def _value(key: str, edge: float, actual: float, review: PortfolioReview, pnl: CardPnL,
           kpis: PortfolioKPIs) -> float:  # fmt: skip
    """Annual profit impact of moving ``actual`` to ``edge`` for one KPI."""
    e = review.economics
    if key == "active_rate":
        extra_actives = (edge - actual) * kpis.accounts
        return max(extra_actives * pnl.profit_per_active, 0.0)
    if key == "revolve_rate":
        return (edge - actual) * e.receivables * (e.apr - e.net_credit_loss_rate)
    if key == "net_credit_loss_rate":
        return (actual - edge) * e.receivables
    if key == "rewards_rate":
        return (actual - edge) * e.purchase_volume
    if key == "approval_rate":
        recovered_volume = e.purchase_volume * (edge / actual - 1) if actual else 0.0
        return recovered_volume * (e.interchange_rate - e.network_fee_rate - e.rewards_rate)
    if key == "fraud_bps":
        return (actual - edge) / 1e4 * e.purchase_volume
    raise KeyError(key)  # pragma: no cover


def diagnose(review: PortfolioReview) -> Diagnosis:
    ptype = get_portfolio_type(review.portfolio_type)
    e = review.economics
    kpis = portfolio_kpis(review.accounts, e.active_accounts, e.purchase_volume, e.receivables,
                          e.revolving_balances, review.transactions)  # fmt: skip
    pnl = card_pnl(e)
    values: dict[str, float] = {
        "active_rate": kpis.active_rate,
        "revolve_rate": kpis.revolve_rate,
        "net_credit_loss_rate": e.net_credit_loss_rate,
        "rewards_rate": e.rewards_rate,
        "roa": pnl.roa,
    }
    if review.approval_rate is not None:
        values["approval_rate"] = require_fraction("approval_rate", review.approval_rate)
    if review.fraud_losses is not None:
        fraud = require_non_negative("fraud_losses", review.fraud_losses)
        values["fraud_bps"] = fraud / e.purchase_volume * 1e4 if e.purchase_volume else 0.0

    checks: list[Check] = []
    opportunities: list[Opportunity] = []
    strengths: list[str] = []
    for r in ptype.ranges:
        if r.key not in values:
            continue
        v = values[r.key]
        weak = r.is_weak(v)
        checks.append(Check(r.key, r.label, v, r.low, r.high, r.unit, r.status(v), weak))
        if weak and r.key in OUTCOMES:
            continue  # an outcome of the levers below, not a lever: checked, not sized
        if weak:
            edge = r.low if r.higher_is_better else r.high
            opportunities.append(_opportunity(r, v, edge, review, pnl, kpis))
        elif r.status(v) != "within":
            strengths.append(f"{r.label} is better than the typical range ({_fmt(r, v)})")
    opportunities.sort(key=lambda o: -o.annual_value)
    weak_count = sum(1 for c in checks if c.weak)
    score = round(100 * (1 - weak_count / len(checks))) if checks else 100
    return Diagnosis(
        review=review,
        portfolio_type=ptype,
        kpis=kpis,
        pnl=pnl,
        checks=tuple(checks),
        opportunities=tuple(opportunities),
        total_opportunity=sum(o.annual_value for o in opportunities),
        health_score=score,
        strengths=tuple(strengths),
    )


def _fmt(r: KPIRange, v: float) -> str:
    if r.unit == "bp":
        return f"{v:.1f} bp"
    return f"{v * 100:.1f}%"


def _opportunity(r: KPIRange, v: float, edge: float, review: PortfolioReview, pnl: CardPnL,
                 kpis: PortfolioKPIs) -> Opportunity:  # fmt: skip
    direction = "Raise" if r.higher_is_better else "Reduce"
    value = _value(r.key, edge, v, review, pnl, kpis)
    detail = (
        f"{r.label} is {_fmt(r, v)} against a typical {_fmt(r, r.low)}-{_fmt(r, r.high)} for "
        f"this portfolio type. Reaching {_fmt(r, edge)} is worth about "
        f"{review.currency}{value / 1e6:,.1f}M a year before tax."
    )
    return Opportunity(r.key, f"{direction} {r.label.lower()}", detail, value, LEVERS[r.key])
