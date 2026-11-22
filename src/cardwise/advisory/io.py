"""Read a portfolio review from JSON (see ``examples/portfolio-review.json``)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from cardwise.advisory.diagnose import PortfolioReview
from cardwise.core.errors import ValidationError
from cardwise.core.parse import from_dict
from cardwise.issuing.pnl import CardEconomics


def review_from_dict(data: object) -> PortfolioReview:
    if not isinstance(data, Mapping):
        raise ValidationError("review must be an object")
    body: dict[str, Any] = dict(data)
    if "economics" not in body:
        raise ValidationError("review: missing 'economics'")
    body["economics"] = from_dict(CardEconomics, body["economics"], "economics")
    return from_dict(PortfolioReview, body, "review")
