import dataclasses

from cardwise.advisory.diagnose import diagnose
from cardwise.advisory.report import render_report, render_summary
from tests.test_diagnose import ECON, REVIEW


def test_report_sections_and_numbers() -> None:
    d = diagnose(REVIEW)
    md = render_report(d)
    for heading in ("## 1.", "## 2.", "## 3.", "## 4.", "## 5."):
        assert heading in md
    assert md.startswith("# Portfolio review: Demo Bank")
    assert d.opportunities[0].title in md
    assert "**gap**" in md
    assert "Pre-tax profit" in md
    text = render_summary(d)
    assert "Top opportunities" in text
    assert "GAP" in text


def test_report_for_a_strong_portfolio() -> None:
    econ = dataclasses.replace(
        ECON,
        active_accounts=800_000,
        revolving_balances=1.6e9,
        net_credit_loss_rate=0.02,
        rewards_rate=0.002,
        fee_income=150e6,
    )
    d = diagnose(
        dataclasses.replace(
            REVIEW,
            economics=econ,
            approval_rate=0.95,
            fraud_losses=1e6,
            transactions=None,
            currency="€",
        )
    )
    md = render_report(d)
    assert "every KPI checked is within" in md
    assert "No KPI gaps" in md
    assert "## 6. Strengths" in md
    assert "€" in md
    assert "Top opportunities" not in render_summary(d)
