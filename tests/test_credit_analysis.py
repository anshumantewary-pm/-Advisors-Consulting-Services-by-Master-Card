import pytest

from cardwise.credit.analysis import (
    debt_capacity,
    exposure_at_default,
    irb_capital,
    loss_given_default,
    pro_forma,
    returns,
    spread,
)
from cardwise.credit.model import (
    BankPolicy,
    Collateral,
    FacilityRequest,
)
from tests.credit_helpers import fin


def test_spread_ratios() -> None:
    s = spread(fin(current_assets=30e6, current_liabilities=20e6, equity=50e6), fin(revenue=80e6))
    assert s.leverage == pytest.approx(2.0)
    assert s.net_leverage == pytest.approx(35 / 20)
    assert s.icr == pytest.approx(10.0)
    assert s.cash_flow_available == pytest.approx(14e6)
    assert s.dscr == pytest.approx(14 / 6)
    assert s.free_cash_flow == pytest.approx(12e6)
    assert s.payback_years == pytest.approx(35 / 12)
    assert s.revenue_growth == pytest.approx(0.25)
    assert s.current_ratio == pytest.approx(1.5)
    assert s.gearing == pytest.approx(0.8)


def test_spread_handles_missing_and_negative_figures() -> None:
    s = spread(fin(ebitda=-1e6, interest_expense=0, scheduled_principal=0, equity=-5e6))
    assert s.leverage is None
    assert s.icr is None
    assert s.dscr is None
    assert s.payback_years is None
    assert s.gearing is None
    assert s.current_ratio is None
    assert s.revenue_growth is None


def test_pro_forma_refinances_pro_rata() -> None:
    req = FacilityRequest(
        amount=30e6, tenor_years=5, margin=0.02, base_rate=0.05, amortisation=0.1, refinances=20e6
    )
    pf = pro_forma(fin(), req)
    assert pf.total_debt == pytest.approx(50e6)
    assert pf.interest_expense == pytest.approx(1e6 + 30e6 * 0.07)
    assert pf.scheduled_principal == pytest.approx(2e6 + 3e6)


def test_pro_forma_revolver_uses_expected_draw_and_handles_no_debt() -> None:
    req = FacilityRequest(
        amount=10e6, tenor_years=3, facility_type="revolver", expected_utilisation=0.4
    )
    pf = pro_forma(fin(total_debt=0, interest_expense=0, scheduled_principal=0), req)
    assert pf.total_debt == pytest.approx(4e6)
    assert pf.interest_expense == pytest.approx(4e6 * req.all_in_rate)


def test_debt_capacity() -> None:
    req = FacilityRequest(
        amount=10e6, tenor_years=5, base_rate=0.05, margin=0.03, amortisation=0.12
    )
    cap = debt_capacity(fin(), req, max_leverage=3.0, policy=BankPolicy())
    assert cap.by_leverage == pytest.approx(20e6)
    assert cap.by_dscr == pytest.approx((14e6 / 1.25 - 6e6) / 0.20)
    assert cap.max_additional == pytest.approx(min(cap.by_leverage, cap.by_dscr))
    free = FacilityRequest(amount=1e6, tenor_years=1, base_rate=0, margin=0)
    assert debt_capacity(fin(), free, 3.0, BankPolicy()).by_dscr == float("inf")


def test_ead_and_lgd() -> None:
    policy = BankPolicy()
    assert exposure_at_default(FacilityRequest(10e6, 5), policy) == 10e6
    rcf = FacilityRequest(10e6, 3, facility_type="revolver", expected_utilisation=0.5)
    assert exposure_at_default(rcf, policy) == pytest.approx(5e6 + 0.75 * 5e6)
    collateral = (Collateral("real_estate", 10e6), Collateral("cash", 1e6))
    cover = loss_given_default(collateral, 16e6, "senior_secured")
    assert cover.recoverable == pytest.approx(8e6)
    assert cover.coverage == pytest.approx(0.5)
    assert cover.lgd == pytest.approx(0.5 * 0.20 + 0.5 * 0.40)
    assert loss_given_default(collateral, 1e6, "senior_secured").lgd == pytest.approx(0.20)
    unsecured = loss_given_default(collateral, 16e6, "subordinated")
    assert unsecured.recoverable == 0
    assert unsecured.lgd == pytest.approx(0.75)
    assert loss_given_default((), 0, "senior_secured").coverage == 0


def test_irb_capital_matches_basel_reference() -> None:
    # Basel corporate formula, PD 1%, LGD 45%, M 2.5: risk weight about 92.3%.
    k, rwa = irb_capital(0.01, 0.45, 100.0, 2.5)
    assert rwa == pytest.approx(92.32, abs=0.05)
    assert k == pytest.approx(rwa / 1250)
    # PD floor and maturity clamps.
    assert irb_capital(0.0, 0.45, 1, 10)[0] == pytest.approx(irb_capital(0.0005, 0.45, 1, 5)[0])


def test_returns_and_required_margin_hit_the_hurdle() -> None:
    policy = BankPolicy()
    req = FacilityRequest(50e6, 5, margin=0.02, upfront_fee=0.01)
    r = returns(req, 0.01, 0.35, policy)
    assert r.expected_loss == pytest.approx(0.01 * 0.35 * 50e6)
    assert r.fee_income == pytest.approx(50e6 * 0.01 / 5)
    assert r.required_margin is not None
    at_hurdle = returns(
        FacilityRequest(50e6, 5, margin=r.required_margin, upfront_fee=0.01), 0.01, 0.35, policy
    )
    assert at_hurdle.raroc == pytest.approx(policy.hurdle_raroc)
    undrawn = FacilityRequest(
        10e6, 3, facility_type="revolver", expected_utilisation=0.0, commitment_fee=0.005
    )
    u = returns(undrawn, 0.01, 0.4, policy)
    assert u.required_margin is None
    assert u.fee_income == pytest.approx(10e6 * 0.005)
