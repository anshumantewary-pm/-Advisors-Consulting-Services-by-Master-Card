import pytest

from cardwise.core.errors import ValidationError
from cardwise.market.sizing import card_market, share_of_wallet


def test_card_market() -> None:
    m = card_market(10e6, 8000, 0.45, 0.05, 0.60, 5, 0.02)
    assert m.consumer_spend == pytest.approx(80e9)
    assert m.card_spend == pytest.approx(36e9)
    future = 80e9 * 1.05**5
    assert m.future_card_spend == pytest.approx(future * 0.6)
    assert m.cash_displaced == pytest.approx(future * 0.15)
    assert m.issuer_revenue_pool == pytest.approx(future * 0.6 * 0.02)
    assert m.steps[-1].value == pytest.approx(m.issuer_revenue_pool)


def test_wallet() -> None:
    w = share_of_wallet(30e6, 100e6, 0.45, main_card_customers=4000, customers=10_000)
    assert w.share_of_wallet == pytest.approx(0.3)
    assert w.top_of_wallet_rate == pytest.approx(0.4)
    assert w.opportunity_at_target == pytest.approx(15e6)
    assert share_of_wallet(0, 0, 0.5).share_of_wallet == 0


def test_errors() -> None:
    with pytest.raises(ValidationError, match="years"):
        card_market(1, 1, 0.1, 0.1, 0.2, -1, 0.01)
    with pytest.raises(ValidationError, match="exceed"):
        share_of_wallet(2, 1, 0.5)
