"""Loss vintages: cumulative loss curves by origination cohort and months on book."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from cardwise.core.errors import ValidationError
from cardwise.core.result import Result
from cardwise.core.validate import require_non_negative, require_positive


@dataclass(frozen=True)
class Vintage(Result):
    name: str  # e.g. "2024-Q1"
    originated: float  # balances or limits booked
    monthly_losses: tuple[float, ...]  # net losses in months on book 1, 2, ...


@dataclass(frozen=True)
class VintageCurves(Result):
    curves: dict[str, tuple[float, ...]]  # cumulative loss rate by month on book
    at_month: int  # common month used to compare vintages
    loss_at_month: dict[str, float]
    best: str
    worst: str
    average_curve: tuple[float, ...]  # origination-weighted, over vintages that reached each month


def cumulative_curve(v: Vintage) -> tuple[float, ...]:
    base = require_positive(f"{v.name}.originated", v.originated)
    total, out = 0.0, []
    for i, loss in enumerate(v.monthly_losses):
        total += require_non_negative(f"{v.name}.monthly_losses[{i}]", loss)
        out.append(total / base)
    return tuple(out)


def vintage_curves(vintages: Sequence[Vintage], at_month: int | None = None) -> VintageCurves:
    if not vintages:
        raise ValidationError("give at least one vintage")
    curves = {v.name: cumulative_curve(v) for v in vintages}
    if len(curves) != len(vintages):
        raise ValidationError("vintage names must be unique")
    shortest = min(len(c) for c in curves.values())
    if shortest == 0:
        raise ValidationError("every vintage needs at least one month of losses")
    month = shortest if at_month is None else at_month
    if not 1 <= month <= shortest:
        raise ValidationError(f"at_month must be between 1 and {shortest}")
    at = {k: c[month - 1] for k, c in curves.items()}
    longest = max(len(c) for c in curves.values())
    weights = {v.name: v.originated for v in vintages}
    average = []
    for m in range(longest):
        live = [k for k, c in curves.items() if len(c) > m]
        w = sum(weights[k] for k in live)
        average.append(sum(curves[k][m] * weights[k] for k in live) / w)
    return VintageCurves(
        curves=curves,
        at_month=month,
        loss_at_month=at,
        best=min(at, key=at.__getitem__),
        worst=max(at, key=at.__getitem__),
        average_curve=tuple(average),
    )


def lifetime_loss_estimate(curve: Sequence[float], seasoning: Mapping[int, float]) -> float:
    """Extrapolate a young vintage: loss at month m / share of lifetime loss usually seen by m.

    ``seasoning`` maps months on book to the share of lifetime losses a mature
    vintage had reached by then (from the bank's own history).
    """
    if not curve:
        raise ValidationError("curve must not be empty")
    m = len(curve)
    if m not in seasoning:
        raise ValidationError(f"seasoning has no entry for month {m}")
    share = seasoning[m]
    if not 0 < share <= 1:
        raise ValidationError("seasoning shares must be in (0, 1]")
    return curve[-1] / share
