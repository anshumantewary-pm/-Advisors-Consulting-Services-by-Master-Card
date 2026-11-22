"""RFM segmentation: recency, frequency and monetary value scored 1-5.

Scores are quintiles within the customer base (5 is best: most recent, most
frequent, highest spend). Named segments follow the common R x F grid.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from cardwise.core.result import Result
from cardwise.core.validate import require_non_empty, require_non_negative


@dataclass(frozen=True)
class Customer(Result):
    id: str
    days_since_last: float
    transactions: float
    spend: float


@dataclass(frozen=True)
class RFMScore(Result):
    id: str
    r: int
    f: int
    m: int
    code: str  # e.g. "545"
    segment: str


@dataclass(frozen=True)
class RFMResult(Result):
    scores: tuple[RFMScore, ...]
    segment_counts: dict[str, int]
    segment_spend: dict[str, float]


def quintile_scores(values: Sequence[float], higher_is_better: bool = True) -> tuple[int, ...]:
    """1-5 score by rank; ties share the score of their first position."""
    n = len(values)
    order = sorted(range(n), key=lambda i: values[i], reverse=not higher_is_better)
    scores = [0] * n
    first_rank: dict[float, int] = {}
    for rank, i in enumerate(order):
        rank = first_rank.setdefault(values[i], rank)
        scores[i] = 1 + (rank * 5) // n
    return tuple(scores)


def segment(r: int, f: int) -> str:
    if r >= 4 and f >= 4:
        return "Champions"
    if r >= 3 and f >= 3:
        return "Loyal"
    if r >= 4 and f <= 2:
        return "New / promising"
    if r <= 2 and f >= 4:
        return "Can't lose them"
    if r <= 2 and f >= 2:
        return "At risk"
    if r == 3:
        return "Needs attention"
    return "Hibernating"


def rfm(customers: Sequence[Customer]) -> RFMResult:
    require_non_empty("customers", customers)
    for c in customers:
        require_non_negative(f"{c.id}.days_since_last", c.days_since_last)
        require_non_negative(f"{c.id}.transactions", c.transactions)
        require_non_negative(f"{c.id}.spend", c.spend)
    r = quintile_scores([c.days_since_last for c in customers], higher_is_better=False)
    f = quintile_scores([c.transactions for c in customers])
    m = quintile_scores([c.spend for c in customers])
    scores = tuple(
        RFMScore(c.id, ri, fi, mi, f"{ri}{fi}{mi}", segment(ri, fi))
        for c, ri, fi, mi in zip(customers, r, f, m, strict=True)
    )
    spend: dict[str, float] = {}
    for c, s in zip(customers, scores, strict=True):
        spend[s.segment] = spend.get(s.segment, 0.0) + c.spend
    return RFMResult(scores, dict(Counter(s.segment for s in scores)), spend)
