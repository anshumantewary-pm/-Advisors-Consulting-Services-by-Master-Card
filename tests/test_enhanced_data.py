import pytest

from cardwise.acquiring.enhanced_data import enhanced_data_savings
from cardwise.core.errors import ValidationError


def test_savings() -> None:
    s = enhanced_data_savings(20e6, 0.025, 0.02, 0.016, 0.1, 0.0, 0.3, 0.5, 60_000)
    today = 0.9 * 0.025 + 0.1 * 0.02
    after = 0.2 * 0.025 + 0.3 * 0.02 + 0.5 * 0.016
    assert s.effective_rate_today == pytest.approx(today)
    assert s.effective_rate_after == pytest.approx(after)
    assert s.annual_saving == pytest.approx(20e6 * (today - after))
    assert s.payback_months == pytest.approx(60_000 / (s.annual_saving / 12))


def test_no_saving_and_errors() -> None:
    s = enhanced_data_savings(1e6, 0.02, 0.02, 0.02, 0, 0, 0.5, 0.5, 1000)
    assert s.annual_saving == 0
    assert s.payback_months is None
    with pytest.raises(ValidationError, match="more than 1"):
        enhanced_data_savings(1, 0.02, 0.02, 0.02, 0.6, 0.6, 0, 0)
