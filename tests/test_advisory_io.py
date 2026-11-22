import pytest

from cardwise.advisory.io import review_from_dict
from cardwise.core.errors import ValidationError

GOOD = {
    "name": "Demo",
    "portfolio_type": "mass_credit",
    "accounts": 1000,
    "economics": {
        "active_accounts": 600,
        "purchase_volume": 6e6,
        "receivables": 2e6,
        "revolving_balances": 1e6,
    },
    "approval_rate": 0.9,
}


def test_reads_review() -> None:
    r = review_from_dict(GOOD)
    assert r.economics.receivables == 2e6
    assert r.economics.apr == 0.20
    assert r.approval_rate == 0.9
    assert r.fraud_losses is None


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ([], "must be an object"),
        ({"name": "x"}, "missing 'economics'"),
        ({**GOOD, "economics": {"receivables": 1}}, "economics: missing"),
        ({**GOOD, "extra": 1}, "unknown field"),
    ],
)
def test_errors(data: object, message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        review_from_dict(data)
