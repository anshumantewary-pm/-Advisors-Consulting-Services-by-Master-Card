"""Built-in models: the suite's calculators as named what-if models for the CLI and web app."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from cardwise.core.errors import UnknownNameError
from cardwise.customer.clv import lifetime_value
from cardwise.issuing.pnl import CardEconomics, card_pnl
from cardwise.issuing.rewards import rewards_programme
from cardwise.whatif.model import Inputs, Model


@dataclass(frozen=True)
class BuiltinModel:
    name: str
    description: str
    output: str
    defaults: Mapping[str, float]
    fn: Model


def _card_profit(x: Inputs) -> float:
    return card_pnl(CardEconomics(**{k: float(v) for k, v in x.items()})).pre_tax_profit


def _rewards(x: Inputs) -> float:
    return rewards_programme(**{k: float(v) for k, v in x.items()}).net_benefit


def _clv(x: Inputs) -> float:
    return lifetime_value(x["annual_margin"], x["retention"], x["discount_rate"]).clv


def _merchant_margin(x: Inputs) -> float:
    return x["volume"] * (x["mdr"] - x["interchange_rate"] - x["scheme_fee_rate"])


MODELS: dict[str, BuiltinModel] = {
    m.name: m
    for m in (
        BuiltinModel(
            "card",
            "Credit card portfolio pre-tax profit",
            "pre-tax profit",
            {
                "active_accounts": 600_000,
                "purchase_volume": 6e9,
                "receivables": 2.4e9,
                "revolving_balances": 1.2e9,
                "interchange_rate": 0.018,
                "apr": 0.20,
                "fee_income": 60e6,
                "cost_of_funds": 0.045,
                "rewards_rate": 0.008,
                "net_credit_loss_rate": 0.035,
                "network_fee_rate": 0.0012,
                "cost_per_account": 60.0,
            },
            _card_profit,
        ),
        BuiltinModel(
            "rewards",
            "Rewards programme net benefit",
            "net benefit",
            {
                "participants": 100_000,
                "spend_per_participant": 12_000,
                "spend_lift": 0.10,
                "points_per_unit": 1.0,
                "point_value": 0.01,
                "breakage": 0.25,
                "interchange_rate": 0.02,
                "network_fee_rate": 0.002,
                "fixed_cost": 1e6,
            },
            _rewards,
        ),
        BuiltinModel(
            "clv",
            "Customer lifetime value",
            "CLV",
            {"annual_margin": 200, "retention": 0.85, "discount_rate": 0.10},
            _clv,
        ),
        BuiltinModel(
            "merchant",
            "Acquirer margin on one merchant",
            "acquirer margin",
            {"volume": 10e6, "mdr": 0.015, "interchange_rate": 0.0049, "scheme_fee_rate": 0.0015},
            _merchant_margin,
        ),
    )
}


def get_model(name: str) -> BuiltinModel:
    try:
        return MODELS[name]
    except KeyError:
        raise UnknownNameError(f"no model {name!r}; available: {', '.join(MODELS)}") from None
