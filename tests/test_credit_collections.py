from typing import Any

import pytest

from cardwise.core.errors import ValidationError
from cardwise.credit.collections import monitor, render_monitoring, status_from_dict
from tests.credit_helpers import load, status


def test_watchlist_account_goes_to_restructuring() -> None:
    m = monitor(status_from_dict(load("coastal-retail-q3-review")))
    assert m.classification == "Substandard"
    assert m.ifrs9_stage == 2
    assert m.sma_bucket == "SMA-0"
    assert m.strategy == "restructure"
    assert all(t.breached for t in m.covenant_tests)
    signals = {s.signal for s in m.signals}
    assert {"Facility near fully drawn", "Utilisation rising fast", "Tight liquidity"} <= signals
    assert m.signals[0].severity in ("high", "critical")
    assert m.ecl > 0
    assert "RESTRUCTURE" in render_monitoring(m)


def test_defaulted_account_goes_to_recovery() -> None:
    m = monitor(status_from_dict(load("meridian-default")))
    assert m.current_grade.grade == 10
    assert m.classification == "Doubtful"
    assert m.ifrs9_stage == 3
    assert m.sma_bucket == "NPA"
    assert m.strategy == "recover"
    assert m.ecl == pytest.approx(m.lgd * m.status.outstanding)
    assert m.recovery_value == pytest.approx(m.status.outstanding * (1 - m.lgd))


def _healthy() -> dict[str, Any]:
    good = {
        "period": "FY",
        "revenue": 500e6,
        "ebitda": 80e6,
        "interest_expense": 8e6,
        "total_debt": 150e6,
        "cash": 20e6,
        "capex": 10e6,
        "taxes": 8e6,
        "scheduled_principal": 10e6,
    }
    return status(
        financials=[good],
        days_past_due=0,
        utilisation_history=[0.5],
        events=[],
        origination_grade=6,
        qualitative={"management": 4, "market_position": 4},
    )


def test_healthy_account_is_monitored() -> None:
    m = monitor(status_from_dict(_healthy()))
    assert m.classification == "Pass"
    assert m.ifrs9_stage == 1
    assert m.sma_bucket == "Standard"
    assert m.strategy == "monitor"
    assert not m.signals
    assert m.migration <= 0
    assert "none" in render_monitoring(m)


def test_thin_headroom_means_watchlist() -> None:
    data = _healthy()
    data["covenants"] = {"max_leverage": 1.95}
    m = monitor(status_from_dict(data))
    assert m.strategy == "watchlist"
    assert m.signals[0].signal.endswith("headroom thin")


def test_single_breach_means_remediation() -> None:
    data = _healthy()
    data["covenants"] = {"min_icr": 12.0}
    m = monitor(status_from_dict(data))
    assert m.strategy in ("remediate", "restructure")
    assert m.current_grade.grade >= 7


@pytest.mark.parametrize(
    ("dpd", "bucket"), [(5, "SMA-0"), (45, "SMA-1"), (75, "SMA-2"), (200, "NPA")]
)
def test_arrears_buckets(dpd: int, bucket: str) -> None:
    m = monitor(status_from_dict(status(days_past_due=dpd)))
    assert m.sma_bucket == bucket


def test_loss_classification_when_unsecured_and_long_overdue() -> None:
    m = monitor(status_from_dict(status(days_past_due=200, collateral=[])))
    assert m.classification == "Loss"
    assert m.strategy == "recover"


def test_well_secured_default_is_substandard_not_doubtful() -> None:
    m = monitor(
        status_from_dict(status(days_past_due=100, collateral=[{"type": "cash", "value": 60e6}]))
    )
    assert m.classification == "Substandard"


def test_covenant_with_no_ebitda_fails() -> None:
    data = _healthy()
    data["financials"][0]["ebitda"] = -1e6
    data["covenants"] = {"max_leverage": 4.0, "min_dscr": 1.1}
    m = monitor(status_from_dict(data))
    leverage, dscr = m.covenant_tests
    assert leverage.breached
    assert leverage.headroom is None
    assert dscr.breached
    assert dscr.actual is not None
    assert dscr.actual < 0


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"origination_grade": 11}, "origination_grade"),
        ({"covenants": {"max_capex": 1}}, "unknown covenant"),
        ({"covenants": [1]}, "covenants must be an object"),
        ({"seniority": "junior"}, "seniority"),
        ({"days_past_due": -1}, "days_past_due"),
        ({"utilisation_history": 0.5}, "utilisation_history"),
        ({"utilisation_history": [1.5]}, "utilisation_history"),
        ({"events": "fraud"}, "events must be a list"),
        ({"events": ["alien_invasion"]}, "unknown event"),
    ],
)
def test_bad_status_files_are_rejected(change: dict[str, Any], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        status_from_dict(status(**change))
