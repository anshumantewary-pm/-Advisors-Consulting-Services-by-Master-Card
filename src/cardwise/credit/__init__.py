"""CreditDecision: borrower in, lending decision and credit memo out, then collections.

One engine for the wholesale credit lifecycle:

    decide(borrower_from_dict(json))   spread, pro forma, rate, LGD, capital, RAROC,
                                       policy checks, decision, structure, approver
    render_memo(decision)              the credit memo, every figure from the decision
    monitor(status_from_dict(json))    covenant tests, early warnings, re-rating,
                                       classification, IFRS 9 / SMA, ECL, workout plan

See docs/ARCHITECTURE.md for where it sits in the suite.
"""

from cardwise.credit.analysis import (
    CollateralCover,
    DebtCapacity,
    Returns,
    Spread,
    debt_capacity,
    exposure_at_default,
    irb_capital,
    loss_given_default,
    pro_forma,
    returns,
    spread,
    spread_history,
)
from cardwise.credit.collections import (
    EVENTS,
    FacilityStatus,
    Monitoring,
    monitor,
    render_monitoring,
    status_from_dict,
)
from cardwise.credit.decision import (
    APPROVE,
    APPROVE_WITH_CONDITIONS,
    DECLINE,
    REFER,
    CreditDecision,
    decide,
)
from cardwise.credit.memo import render_memo, render_summary
from cardwise.credit.model import (
    COLLATERAL_HAIRCUTS,
    INDUSTRIES,
    BankPolicy,
    Borrower,
    Collateral,
    FacilityRequest,
    Financials,
    Qualitative,
    borrower_from_dict,
    get_industry,
)
from cardwise.credit.rating import MASTER_SCALE, Grade, Rating, grade, rate

__all__ = [
    "APPROVE",
    "APPROVE_WITH_CONDITIONS",
    "COLLATERAL_HAIRCUTS",
    "DECLINE",
    "EVENTS",
    "INDUSTRIES",
    "MASTER_SCALE",
    "REFER",
    "BankPolicy",
    "Borrower",
    "Collateral",
    "CollateralCover",
    "CreditDecision",
    "DebtCapacity",
    "FacilityRequest",
    "FacilityStatus",
    "Financials",
    "Grade",
    "Monitoring",
    "Qualitative",
    "Rating",
    "Returns",
    "Spread",
    "borrower_from_dict",
    "debt_capacity",
    "decide",
    "exposure_at_default",
    "get_industry",
    "grade",
    "irb_capital",
    "loss_given_default",
    "monitor",
    "pro_forma",
    "rate",
    "render_memo",
    "render_monitoring",
    "render_summary",
    "returns",
    "spread",
    "spread_history",
    "status_from_dict",
]
