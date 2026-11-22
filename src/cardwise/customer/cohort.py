"""Cohort retention: share of each acquisition cohort still active in later periods."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from cardwise.core.errors import ValidationError
from cardwise.core.result import Result


@dataclass(frozen=True)
class CohortTable(Result):
    cohorts: tuple[str, ...]  # sorted cohort labels
    sizes: dict[str, int]
    retention: dict[str, tuple[float, ...]]  # period offset 0, 1, 2 ... (offset 0 is 1.0)
    average: tuple[float, ...]  # size-weighted over cohorts old enough for each offset


def cohort_retention(activity: Iterable[tuple[str, int, int]]) -> CohortTable:
    """Build a retention table from ``(customer_id, cohort_period, active_period)`` rows.

    Periods are integers (e.g. months since a fixed start). A customer's cohort is
    the period they joined; every active period at or after it counts once.
    """
    joined: dict[str, int] = {}
    active: dict[str, set[int]] = {}
    last_period = None
    for cid, cohort, period in activity:
        if period < cohort:
            raise ValidationError(f"customer {cid} is active in {period} before joining in {cohort}")
        if joined.setdefault(cid, cohort) != cohort:
            raise ValidationError(f"customer {cid} has two cohorts")
        active.setdefault(cid, set()).add(period)
        last_period = period if last_period is None else max(last_period, period)
    if last_period is None:
        raise ValidationError("no activity rows")
    by_cohort: dict[int, list[str]] = {}
    for cid, c in joined.items():
        by_cohort.setdefault(c, []).append(cid)
    retention: dict[str, tuple[float, ...]] = {}
    sizes: dict[str, int] = {}
    for c in sorted(by_cohort):
        members = by_cohort[c]
        span = last_period - c + 1
        row = tuple(sum(1 for m in members if c + k in active[m]) / len(members) for k in range(span))
        retention[str(c)] = (1.0, *row[1:])
        sizes[str(c)] = len(members)
    longest = max(len(r) for r in retention.values())
    average = []
    for k in range(longest):
        live = [c for c, r in retention.items() if len(r) > k]
        w = sum(sizes[c] for c in live)
        average.append(sum(retention[c][k] * sizes[c] for c in live) / w)
    return CohortTable(tuple(retention), sizes, retention, tuple(average))
