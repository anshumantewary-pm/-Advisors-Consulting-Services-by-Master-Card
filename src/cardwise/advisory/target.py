"""Target state: the P&L if a share of each KPI gap were closed, bridged from today.

Where ``diagnose`` sizes each gap on its own, ``target_state`` changes the
inputs together and recomputes the full P&L, so overlaps between levers are
handled by the model rather than double-counted.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from dataclasses import dataclass

from cardwise.advisory.diagnose import Diagnosis
from cardwise.core.errors import ValidationError
from cardwise.core.result import Result
from cardwise.core.validate import require_fraction
from cardwise.issuing.pnl import CardEconomics, PnLBridge, pnl_bridge


@dataclass(frozen=True)
class TargetState(Result):
    achievement: dict[str, float]  # share of each gap closed, 0..1
    economics: CardEconomics  # target-state inputs
    bridge: PnLBridge  # today's pre-tax profit -> target
    roa_before: float
    roa_after: float


def _close(actual: float, edge: float, share: float) -> float:
    return actual + (edge - actual) * share


def target_state(d: Diagnosis, achievement: Mapping[str, float] | float = 1.0) -> TargetState:
    """Close ``achievement`` of each sized gap (a number for all, or a share per KPI)."""
    keys = [o.key for o in d.opportunities]
    if isinstance(achievement, Mapping):
        unknown = sorted(set(achievement) - set(keys))
        if unknown:
            raise ValidationError(f"no opportunity for: {', '.join(unknown)}")
        shares = {k: require_fraction(f"achievement.{k}", achievement.get(k, 0.0)) for k in keys}
    else:
        share = require_fraction("achievement", achievement)
        shares = dict.fromkeys(keys, share)
    e = d.review.economics
    checks = {c.key: c for c in d.checks}
    changes: dict[str, float] = {}
    # Volume-scaling levers first, so later levers apply to the scaled balances.
    order = (
        "active_rate",
        "approval_rate",
        "revolve_rate",
        "net_credit_loss_rate",
        "rewards_rate",
        "fraud_bps",
    )
    for key in sorted(shares, key=order.index):
        share = shares[key]
        c = checks[key]
        edge = c.high if key in ("net_credit_loss_rate", "rewards_rate", "fraud_bps") else c.low
        target = _close(c.value, edge, share)
        if key == "active_rate":
            new_active = target * d.kpis.accounts
            ratio = new_active / e.active_accounts if e.active_accounts else 1.0
            changes["active_accounts"] = new_active
            # New actives spend and borrow like today's average active.
            changes["purchase_volume"] = e.purchase_volume * ratio
            changes["receivables"] = e.receivables * ratio
            changes["revolving_balances"] = e.revolving_balances * ratio
        elif key == "revolve_rate":
            receivables = changes.get("receivables", e.receivables)
            changes["revolving_balances"] = target * receivables
        elif key in ("net_credit_loss_rate", "rewards_rate"):
            changes[key] = target
        elif key == "approval_rate":
            volume = changes.get("purchase_volume", e.purchase_volume)
            changes["purchase_volume"] = volume * target / c.value
        elif key == "fraud_bps":
            pass  # fraud losses sit outside the card P&L inputs; valued in the diagnosis only
    after = dataclasses.replace(e, **changes)
    bridge = pnl_bridge(e, after)
    roa_after = bridge.after / after.receivables
    return TargetState(shares, after, bridge, bridge.before / e.receivables, roa_after)
