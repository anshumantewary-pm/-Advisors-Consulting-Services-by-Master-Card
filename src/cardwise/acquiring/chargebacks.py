"""Chargeback cost and the case for fighting them (representment)."""

from __future__ import annotations

from dataclasses import dataclass

from cardwise.core.result import Result
from cardwise.core.validate import require_fraction, require_non_negative


@dataclass(frozen=True)
class ChargebackCost(Result):
    chargebacks: float
    gross_loss: float  # value of disputed sales
    fees: float
    handling_cost: float
    recovered: float  # value won back through representment
    net_loss: float
    cost_per_chargeback: float
    representment_net_value: float  # recovered - cost of contesting
    contest_recommended: bool


def chargeback_cost(
    chargebacks: float,
    average_value: float,
    fee_per_chargeback: float,
    handling_cost: float,
    contest_rate: float,
    win_rate: float,
    contest_cost: float,
    goods_lost_share: float = 1.0,
) -> ChargebackCost:
    """Total cost of chargebacks and whether contesting them is worth it.

    ``goods_lost_share`` is the share of the sale value lost (1.0 for physical
    goods shipped; lower for digital goods with low marginal cost).
    """
    n = require_non_negative("chargebacks", chargebacks)
    value = require_non_negative("average_value", average_value)
    fee = require_non_negative("fee_per_chargeback", fee_per_chargeback)
    handling = require_non_negative("handling_cost", handling_cost)
    contest = require_fraction("contest_rate", contest_rate)
    win = require_fraction("win_rate", win_rate)
    per_contest = require_non_negative("contest_cost", contest_cost)
    lost_share = require_fraction("goods_lost_share", goods_lost_share)
    gross = n * value * lost_share
    fees = n * fee
    handling_total = n * handling + n * contest * per_contest
    recovered = n * contest * win * value * lost_share
    net = gross + fees + handling_total - recovered
    per_case_value = win * value * lost_share - per_contest
    return ChargebackCost(
        chargebacks=n,
        gross_loss=gross,
        fees=fees,
        handling_cost=handling_total,
        recovered=recovered,
        net_loss=net,
        cost_per_chargeback=net / n if n else 0.0,
        representment_net_value=n * contest * per_case_value,
        contest_recommended=per_case_value > 0,
    )
