"""Card portfolio loss provisions by delinquency bucket: IFRS 9 stages and a lifetime view.

Stage mapping follows the usual backstops: current and 1-29 days past due are
stage 1 (12-month expected loss), 30-89 days are stage 2 (lifetime), 90+ days
are stage 3 (credit-impaired, PD = 1). ``lifetime`` applies lifetime loss to
every bucket, as CECL does.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from cardwise.core.errors import ValidationError
from cardwise.core.result import Result
from cardwise.core.validate import require_fraction, require_non_negative, require_positive

STAGES: dict[str, int] = {
    "current": 1,
    "1-29": 1,
    "30-59": 2,
    "60-89": 2,
    "90-119": 3,
    "120-149": 3,
}


@dataclass(frozen=True)
class BucketProvision(Result):
    bucket: str
    stage: int
    balance: float
    pd_12m: float
    pd_lifetime: float
    ecl: float


@dataclass(frozen=True)
class Provision(Result):
    buckets: tuple[BucketProvision, ...]
    stage_balances: dict[str, float]
    stage_ecl: dict[str, float]
    total_balance: float
    ifrs9_ecl: float
    lifetime_ecl: float  # CECL-style: lifetime loss on every bucket
    coverage: float  # IFRS 9 ECL / balances
    lifetime_coverage: float


def lifetime_pd(pd_12m: float, years: float) -> float:
    """Constant-hazard lifetime PD: 1 - (1 - PD12m) ^ years."""
    pd = require_fraction("pd_12m", pd_12m)
    n = require_positive("years", years)
    survival: float = (1 - pd) ** n
    return 1 - survival


def provision(
    balances: Mapping[str, float],
    pd_12m: Mapping[str, float],
    lgd: float,
    lifetime_years: float = 2.5,
) -> Provision:
    """ECL by bucket. ``pd_12m`` gives the 12-month PD for each non-impaired bucket."""
    loss = require_fraction("lgd", lgd)
    rows = []
    for bucket, balance in balances.items():
        if bucket not in STAGES:
            raise ValidationError(f"unknown bucket {bucket!r}; use {', '.join(STAGES)}")
        bal = require_non_negative(f"balances.{bucket}", balance)
        stage = STAGES[bucket]
        if stage == 3:
            p12 = plife = 1.0
        else:
            if bucket not in pd_12m:
                raise ValidationError(f"pd_12m has no value for bucket {bucket!r}")
            p12 = require_fraction(f"pd_12m.{bucket}", pd_12m[bucket])
            plife = lifetime_pd(p12, lifetime_years)
        pd_used = p12 if stage == 1 else plife
        rows.append(BucketProvision(bucket, stage, bal, p12, plife, bal * pd_used * loss))
    if not rows:
        raise ValidationError("balances must not be empty")
    stage_bal = {f"stage {s}": sum(r.balance for r in rows if r.stage == s) for s in (1, 2, 3)}
    stage_ecl = {f"stage {s}": sum(r.ecl for r in rows if r.stage == s) for s in (1, 2, 3)}
    total = sum(r.balance for r in rows)
    ifrs9 = sum(r.ecl for r in rows)
    life = sum(r.balance * r.pd_lifetime * loss for r in rows)
    return Provision(
        buckets=tuple(rows),
        stage_balances=stage_bal,
        stage_ecl=stage_ecl,
        total_balance=total,
        ifrs9_ecl=ifrs9,
        lifetime_ecl=life,
        coverage=ifrs9 / total if total else 0.0,
        lifetime_coverage=life / total if total else 0.0,
    )
