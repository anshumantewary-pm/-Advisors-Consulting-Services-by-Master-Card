"""Fraud strategy economics: losses caught vs good customers declined.

A fraud rule or model is a trade-off. Declining a fraudulent transaction saves
its value; declining a good one loses its margin and, often, the customer's
future spend. ``rule_economics`` prices one confusion matrix and
``best_threshold`` picks the score cut-off with the lowest total cost.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from cardwise.core.result import Result
from cardwise.core.validate import require_fraction, require_non_empty, require_non_negative


def fraud_rate_bps(fraud_value: float, sales_value: float) -> float:
    """Fraud losses in basis points of sales, the industry's standard yardstick."""
    require_non_negative("fraud_value", fraud_value)
    sales = require_non_negative("sales_value", sales_value)
    return fraud_value / sales * 1e4 if sales else 0.0


@dataclass(frozen=True)
class RuleEconomics(Result):
    true_positives: float  # fraud declined
    false_positives: float  # good declined
    false_negatives: float  # fraud approved
    true_negatives: float  # good approved
    precision: float  # share of declines that were fraud
    recall: float  # share of fraud caught
    decline_rate: float
    false_positive_ratio: float | None  # good declined per fraud caught
    fraud_prevented: float
    fraud_missed: float
    insult_cost: float  # lost margin and churn from declining good customers
    total_cost: float  # fraud missed + insult cost


def rule_economics(
    true_positives: float,
    false_positives: float,
    false_negatives: float,
    true_negatives: float,
    average_fraud_value: float,
    average_good_value: float,
    margin: float,
    churn_cost_per_false_decline: float = 0.0,
) -> RuleEconomics:
    tp = require_non_negative("true_positives", true_positives)
    fp = require_non_negative("false_positives", false_positives)
    fn = require_non_negative("false_negatives", false_negatives)
    tn = require_non_negative("true_negatives", true_negatives)
    fraud_value = require_non_negative("average_fraud_value", average_fraud_value)
    good_value = require_non_negative("average_good_value", average_good_value)
    require_fraction("margin", margin)
    churn = require_non_negative("churn_cost_per_false_decline", churn_cost_per_false_decline)
    total = tp + fp + fn + tn
    insult = fp * (good_value * margin + churn)
    missed = fn * fraud_value
    return RuleEconomics(
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
        true_negatives=tn,
        precision=tp / (tp + fp) if tp + fp else 0.0,
        recall=tp / (tp + fn) if tp + fn else 0.0,
        decline_rate=(tp + fp) / total if total else 0.0,
        false_positive_ratio=fp / tp if tp else None,
        fraud_prevented=tp * fraud_value,
        fraud_missed=missed,
        insult_cost=insult,
        total_cost=missed + insult,
    )


@dataclass(frozen=True)
class Scored(Result):
    """One transaction: model score (higher = riskier), fraud label and value."""

    score: float
    is_fraud: bool
    value: float


@dataclass(frozen=True)
class ThresholdChoice(Result):
    threshold: float  # decline when score >= threshold
    total_cost: float
    fraud_missed: float
    insult_cost: float
    decline_rate: float
    recall: float
    curve: tuple[tuple[float, float], ...]  # (threshold, total cost) for every candidate


def best_threshold(
    transactions: Sequence[Scored], margin: float, churn_cost_per_false_decline: float = 0.0
) -> ThresholdChoice:
    """Cut-off that minimises missed fraud plus the cost of declining good customers.

    Candidates are every distinct score plus "decline nothing" (above the top score).
    """
    require_non_empty("transactions", transactions)
    require_fraction("margin", margin)
    churn = require_non_negative("churn_cost_per_false_decline", churn_cost_per_false_decline)
    for i, t in enumerate(transactions):
        require_non_negative(f"transactions[{i}].value", t.value)
    total_fraud = sum(t.value for t in transactions if t.is_fraud)
    n_fraud = sum(1 for t in transactions if t.is_fraud)
    candidates = [*sorted({t.score for t in transactions}), float("inf")]
    curve = []
    best: tuple[float, float, float, float, float, float] | None = None
    for th in candidates:
        declined = [t for t in transactions if t.score >= th]
        caught = sum(t.value for t in declined if t.is_fraud)
        insult = sum(t.value * margin + churn for t in declined if not t.is_fraud)
        missed = total_fraud - caught
        cost = missed + insult
        curve.append((th, cost))
        if best is None or cost < best[1] - 1e-12:
            recall = sum(1 for t in declined if t.is_fraud) / n_fraud if n_fraud else 0.0
            best = (th, cost, missed, insult, len(declined) / len(transactions), recall)
    assert best is not None
    th, cost, missed, insult, rate, recall = best
    return ThresholdChoice(th, cost, missed, insult, rate, recall, tuple(curve))
