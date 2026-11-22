"""Payments market sizing: how much consumer spend moves to cards, and what it is worth."""

from __future__ import annotations

from dataclasses import dataclass

from cardwise.core.errors import ValidationError
from cardwise.core.result import Result, Step
from cardwise.core.validate import require_fraction, require_non_negative, require_positive


@dataclass(frozen=True)
class CardMarket(Result):
    consumer_spend: float
    card_spend: float
    cash_and_other: float
    card_penetration: float
    future_card_spend: float  # after the forecast years
    cash_displaced: float  # card spend gained from cash and other methods
    issuer_revenue_pool: float  # future card spend x revenue yield
    steps: tuple[Step, ...]


def card_market(
    population: float,
    spend_per_capita: float,
    card_share: float,
    spend_growth: float,
    target_card_share: float,
    years: int,
    revenue_yield: float,
) -> CardMarket:
    """Top-down card market: personal consumption x card share, grown and shifted.

    ``target_card_share`` is the card share of spend expected after ``years``;
    ``revenue_yield`` is total industry revenue (interchange plus fees) per unit
    of card spend.
    """
    pop = require_positive("population", population)
    per_capita = require_non_negative("spend_per_capita", spend_per_capita)
    share = require_fraction("card_share", card_share)
    growth = require_non_negative("spend_growth", spend_growth)
    target = require_fraction("target_card_share", target_card_share)
    yield_ = require_fraction("revenue_yield", revenue_yield)
    if isinstance(years, bool) or not isinstance(years, int) or years < 0:
        raise ValidationError(f"years must be a whole number >= 0, got {years!r}")
    spend = pop * per_capita
    card = spend * share
    future_spend = spend * (1 + growth) ** years
    future_card = future_spend * target
    displaced = future_card - future_spend * share
    steps = (
        Step("Consumer spend", spend, "$"),
        Step("Card share today", share, "%"),
        Step("Card spend today", card, "$"),
        Step(f"Consumer spend in {years} years", future_spend, "$"),
        Step("Target card share", target, "%"),
        Step("Card spend then", future_card, "$"),
        Step("Of which shifted from cash and other", displaced, "$"),
        Step("Revenue pool", future_card * yield_, "$"),
    )
    return CardMarket(
        spend, card, spend - card, share, future_card, displaced, future_card * yield_, steps
    )


@dataclass(frozen=True)
class Wallet(Result):
    customer_card_spend: float  # spend on our card
    customer_total_spend: float  # all card spend of the same customers
    share_of_wallet: float
    top_of_wallet_rate: float | None  # share of customers for whom we are the main card
    opportunity_at_target: float  # extra spend if share of wallet reached the target


def share_of_wallet(
    our_spend: float,
    total_spend: float,
    target_share: float,
    main_card_customers: float | None = None,
    customers: float | None = None,
) -> Wallet:
    ours = require_non_negative("our_spend", our_spend)
    total = require_non_negative("total_spend", total_spend)
    if ours > total:
        raise ValidationError("our_spend cannot exceed total_spend")
    target = require_fraction("target_share", target_share)
    share = ours / total if total else 0.0
    tow = None
    if main_card_customers is not None and customers:
        tow = require_non_negative("main_card_customers", main_card_customers) / customers
    return Wallet(ours, total, share, tow, max(target * total - ours, 0.0))
