"""Peer benchmarking: where a client's KPI sits within a peer group."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from cardwise.core.errors import ValidationError
from cardwise.core.result import Result
from cardwise.core.validate import require_number, require_numbers


def percentile(values: Sequence[float], q: float) -> float:
    """Linear-interpolated percentile (the same method as Excel's PERCENTILE.INC)."""
    data = sorted(require_numbers("values", values))
    if not 0 <= q <= 1:
        raise ValidationError(f"q must be between 0 and 1, got {q}")
    pos = q * (len(data) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(data) - 1)
    return data[lo] + (data[hi] - data[lo]) * (pos - lo)


@dataclass(frozen=True)
class PeerPosition(Result):
    metric: str
    value: float
    higher_is_better: bool
    peer_count: int
    median: float
    top_quartile: float  # the "good" end, whichever direction that is
    bottom_quartile: float
    percentile_rank: float  # 0-1, share of peers the client beats
    quartile: int  # 1 is best
    gap_to_median: float  # positive means better than the median
    gap_to_top_quartile: float


def peer_position(
    metric: str, value: float, peers: Sequence[float], higher_is_better: bool = True
) -> PeerPosition:
    v = require_number(metric, value)
    data = require_numbers(f"{metric} peers", peers)
    q25, med, q75 = (percentile(data, q) for q in (0.25, 0.5, 0.75))
    top, bottom = (q75, q25) if higher_is_better else (q25, q75)
    if higher_is_better:
        beaten = sum(1 for p in data if p < v) + 0.5 * sum(1 for p in data if p == v)
    else:
        beaten = sum(1 for p in data if p > v) + 0.5 * sum(1 for p in data if p == v)
    rank = beaten / len(data)
    quartile = 1 if rank >= 0.75 else 2 if rank >= 0.5 else 3 if rank >= 0.25 else 4
    sign = 1 if higher_is_better else -1
    return PeerPosition(
        metric=metric,
        value=v,
        higher_is_better=higher_is_better,
        peer_count=len(data),
        median=med,
        top_quartile=top,
        bottom_quartile=bottom,
        percentile_rank=rank,
        quartile=quartile,
        gap_to_median=sign * (v - med),
        gap_to_top_quartile=sign * (v - top),
    )


def scorecard(
    client: Mapping[str, float],
    peers: Mapping[str, Sequence[float]],
    higher_is_better: Mapping[str, bool],
) -> tuple[PeerPosition, ...]:
    """Position on every metric the client and the peer set share, worst quartile first."""
    shared = [m for m in client if m in peers]
    if not shared:
        raise ValidationError("client and peers share no metrics")
    rows = [peer_position(m, client[m], peers[m], higher_is_better.get(m, True)) for m in shared]
    return tuple(sorted(rows, key=lambda p: (-p.quartile, p.percentile_rank)))
