"""Merchant portfolio profitability: which merchants make or lose money, and what to reprice.

Each merchant's contribution is its acquirer margin (MDR less interchange and
scheme fees, times volume) less its cost to serve. Loss-making merchants get
the MDR that would bring them to a target margin.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from cardwise.core.errors import ValidationError
from cardwise.core.result import Result
from cardwise.core.validate import require_fraction, require_non_negative


@dataclass(frozen=True)
class Merchant(Result):
    name: str
    volume: float
    mdr: float
    interchange_rate: float
    scheme_fee_rate: float
    cost_to_serve: float = 0.0  # annual: terminals, support, risk monitoring


@dataclass(frozen=True)
class MerchantResult(Result):
    name: str
    volume: float
    margin: float  # before cost to serve
    contribution: float  # after cost to serve
    contribution_bps: float  # contribution as basis points of volume
    repriced_mdr: float | None  # MDR that reaches the target contribution, if below it


@dataclass(frozen=True)
class MerchantPortfolio(Result):
    merchants: tuple[MerchantResult, ...]  # worst contribution first
    total_volume: float
    total_contribution: float
    loss_makers: tuple[str, ...]
    repricing_uplift: float  # contribution gained if every merchant below target is repriced
    concentration_top5: float  # share of contribution from the five best merchants


def merchant_portfolio(merchants: Sequence[Merchant], target_bps: float = 0.0) -> MerchantPortfolio:
    if not merchants:
        raise ValidationError("give at least one merchant")
    target = require_non_negative("target_bps", target_bps) / 1e4
    rows = []
    uplift = 0.0
    for m in merchants:
        vol = require_non_negative(f"{m.name}.volume", m.volume)
        for name in ("mdr", "interchange_rate", "scheme_fee_rate"):
            require_fraction(f"{m.name}.{name}", getattr(m, name))
        cts = require_non_negative(f"{m.name}.cost_to_serve", m.cost_to_serve)
        margin = vol * (m.mdr - m.interchange_rate - m.scheme_fee_rate)
        contribution = margin - cts
        bps = contribution / vol * 1e4 if vol else 0.0
        repriced = None
        if vol and contribution < target * vol:
            repriced = m.interchange_rate + m.scheme_fee_rate + (cts / vol) + target
            uplift += target * vol - contribution
        rows.append(MerchantResult(m.name, vol, margin, contribution, bps, repriced))
    rows.sort(key=lambda r: r.contribution)
    total = sum(r.contribution for r in rows)
    best5 = sum(r.contribution for r in sorted(rows, key=lambda r: -r.contribution)[:5])
    return MerchantPortfolio(
        merchants=tuple(rows),
        total_volume=sum(r.volume for r in rows),
        total_contribution=total,
        loss_makers=tuple(r.name for r in rows if r.contribution < 0),
        repricing_uplift=uplift,
        concentration_top5=best5 / total if total > 0 else 0.0,
    )
