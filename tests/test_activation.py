import pytest

from cardwise.core.errors import ValidationError
from cardwise.issuing.activation import activation_campaign


def test_campaign_value() -> None:
    c = activation_campaign(200_000, 0.12, 0.04, 0.5, 25, 180, 0.8, 0.10, 3)
    assert c.incremental_activations == pytest.approx(16_000)
    assert c.campaign_cost == pytest.approx(100_000 + 24_000 * 25)
    v = 180 / 1.1 + 180 * 0.8 / 1.1**2 + 180 * 0.64 / 1.1**3
    assert c.value_per_active == pytest.approx(v)
    assert c.net_value == pytest.approx(16_000 * v - c.campaign_cost)
    assert c.cost_per_incremental == pytest.approx(c.campaign_cost / 16_000)
    assert c.payback_years == 1.0  # first-year value 16,000 x 163.6 already covers 0.7M


def test_campaign_that_never_pays_back() -> None:
    c = activation_campaign(1000, 0.05, 0.05, 1, 50, 100, 0.5)
    assert c.incremental_activations == 0
    assert c.cost_per_incremental is None
    assert c.payback_years is None
    free = activation_campaign(0, 0.1, 0.0, 0, 0, 1, 0.5)
    assert free.roi is None


def test_validation() -> None:
    with pytest.raises(ValidationError, match="adds nothing"):
        activation_campaign(1, 0.01, 0.05, 1, 1, 1, 0.5)
    with pytest.raises(ValidationError, match="years"):
        activation_campaign(1, 0.1, 0.0, 1, 1, 1, 0.5, years=0)
