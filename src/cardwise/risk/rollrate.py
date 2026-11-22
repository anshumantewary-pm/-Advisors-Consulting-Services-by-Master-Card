"""Delinquency roll rates: how balances move between buckets month to month.

Buckets run from ``current`` through days-past-due bands to ``charge_off``
(absorbing). A transition matrix estimated from one month of account moves
projects balances forward and gives the flow-through rate: the share of
today's current balances that ends up charged off.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from cardwise.core.errors import ValidationError
from cardwise.core.result import Result
from cardwise.core.validate import require_count, require_non_negative

BUCKETS: tuple[str, ...] = ("current", "1-29", "30-59", "60-89", "90-119", "120-149", "charge_off")

Matrix = dict[str, dict[str, float]]


def transition_matrix(moves: Mapping[str, Mapping[str, float]]) -> Matrix:
    """Turn ``{from_bucket: {to_bucket: balance}}`` into row-normalised probabilities.

    Charge-off is absorbing whatever the input says. Rows with no balance stay put.
    """
    matrix: Matrix = {}
    for src in BUCKETS:
        row = moves.get(src, {})
        for dst, value in row.items():
            if dst not in BUCKETS:
                raise ValidationError(f"unknown bucket {dst!r}; use {', '.join(BUCKETS)}")
            require_non_negative(f"moves.{src}.{dst}", value)
        total = sum(row.values())
        if src == "charge_off" or total == 0:
            matrix[src] = {b: float(b == src) for b in BUCKETS}
        else:
            matrix[src] = {b: row.get(b, 0.0) / total for b in BUCKETS}
    for src in moves:
        if src not in BUCKETS:
            raise ValidationError(f"unknown bucket {src!r}; use {', '.join(BUCKETS)}")
    return matrix


def roll_rates(matrix: Matrix) -> dict[str, float]:
    """Forward roll rate of each delinquent stage: share moving one bucket worse."""
    return {src: matrix[src][dst] for src, dst in zip(BUCKETS[:-1], BUCKETS[1:], strict=True)}


def project(balances: Mapping[str, float], matrix: Matrix, months: int) -> tuple[dict[str, float], ...]:
    """Balances by bucket for each of the next ``months`` (no new lending, no paydown)."""
    require_count("months", months)
    state = {b: require_non_negative(f"balances.{b}", balances.get(b, 0.0)) for b in BUCKETS}
    for b in balances:
        if b not in BUCKETS:
            raise ValidationError(f"unknown bucket {b!r}")
    path = []
    for _ in range(months):
        state = {dst: sum(state[src] * matrix[src][dst] for src in BUCKETS) for dst in BUCKETS}
        path.append(state)
    return tuple(path)


@dataclass(frozen=True)
class RollRateAnalysis(Result):
    matrix: Matrix
    roll_rates: dict[str, float]
    flow_through: float  # product of forward roll rates from current to charge-off
    projection: tuple[dict[str, float], ...]
    projected_charge_offs: float
    loss_rate: float  # projected charge-offs / starting non-charged-off balances


def analyse(
    moves: Mapping[str, Mapping[str, float]], balances: Mapping[str, float], months: int = 12
) -> RollRateAnalysis:
    matrix = transition_matrix(moves)
    rates = roll_rates(matrix)
    flow = 1.0
    for r in rates.values():
        flow *= r
    path = project(balances, matrix, months)
    start = sum(v for k, v in balances.items() if k != "charge_off")
    charged = path[-1]["charge_off"] - balances.get("charge_off", 0.0)
    return RollRateAnalysis(matrix, rates, flow, path, charged, charged / start if start else 0.0)


def bucket_shares(balances: Sequence[float]) -> dict[str, float]:
    """Share of balances in each bucket, given values in ``BUCKETS`` order."""
    if len(balances) != len(BUCKETS):
        raise ValidationError(f"give {len(BUCKETS)} balances, one per bucket")
    total = sum(require_non_negative(f"balances[{i}]", v) for i, v in enumerate(balances))
    return {b: (v / total if total else 0.0) for b, v in zip(BUCKETS, balances, strict=True)}
