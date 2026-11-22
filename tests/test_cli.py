import json
import subprocess
import sys
from pathlib import Path

import pytest

from cardwise.cli import main, money, pct, read_json, read_text, write_text
from cardwise.core.errors import ValidationError

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


def run(capsys: pytest.CaptureFixture[str], *argv: str) -> str:
    assert main(list(argv)) == 0
    return capsys.readouterr().out


def run_json(capsys: pytest.CaptureFixture[str], *argv: str) -> object:
    return json.loads(run(capsys, *argv, "--json"))


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["--version"])
    assert "cardwise" in capsys.readouterr().out


def test_module_entry_point() -> None:
    out = subprocess.run(
        [sys.executable, "-m", "cardwise", "--version"], capture_output=True, text=True, check=True
    )
    assert out.stdout.startswith("cardwise")


def test_helpers(tmp_path: Path) -> None:
    assert money(2_500_000) == "2.5M"
    assert money(-12.5) == "-12.50"
    assert pct(None) == "n/a"
    target = tmp_path / "x.txt"
    write_text(str(target), "hi")
    assert read_text(str(target)) == "hi"
    bad = tmp_path / "bad.json"
    bad.write_text("{", encoding="utf-8")
    with pytest.raises(ValidationError, match="not valid JSON"):
        read_json(str(bad))
    with pytest.raises(ValidationError, match="cannot read"):
        read_json(str(tmp_path / "missing.json"))
    with pytest.raises(ValidationError, match="cannot read"):
        read_text(str(tmp_path / "missing.txt"))
    with pytest.raises(ValidationError, match="cannot write"):
        write_text(str(tmp_path / "no" / "x.txt"), "x")


def test_review(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    out = run(capsys, "review", str(EXAMPLES / "portfolio-review.json"))
    assert "Harbour Bank Cards" in out
    assert "Top opportunities" in out
    report = tmp_path / "r.md"
    out = run(capsys, "review", str(EXAMPLES / "portfolio-review.json"), "--report", str(report))
    assert report.read_text(encoding="utf-8").startswith("# Portfolio review")
    assert "## 1. Executive summary" in run(
        capsys, "review", str(EXAMPLES / "portfolio-review.json"), "--report", "-"
    )
    data = run_json(capsys, "review", str(EXAMPLES / "portfolio-review.json"))
    assert isinstance(data, dict)
    assert data["opportunities"]
    assert data["report_markdown"].startswith("# Portfolio review")


def test_types(capsys: pytest.CaptureFixture[str]) -> None:
    out = run(capsys, "types")
    assert "mass_credit" in out
    assert "3 - 8 bp" in out
    assert "premium_credit" in run_json(capsys, "types")  # type: ignore[operator]


def test_errors_exit_2(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    assert main(["review", str(tmp_path / "missing.json")]) == 2
    assert "cannot read" in capsys.readouterr().err


def test_pnl(capsys: pytest.CaptureFixture[str]) -> None:
    args = [
        "pnl",
        "--active-accounts",
        "600000",
        "--purchase-volume",
        "6e9",
        "--receivables",
        "2.4e9",
        "--revolving-balances",
        "1.2e9",
        "--fee-income",
        "6e7",
    ]
    out = run(capsys, *args)
    assert "Pre-tax profit" in out
    assert "ROA on receivables" in out
    data = run_json(capsys, *args)
    assert data["interchange"] == pytest.approx(108e6)  # type: ignore[index]


def test_rewards(capsys: pytest.CaptureFixture[str]) -> None:
    base = [
        "rewards",
        "--participants",
        "100000",
        "--spend",
        "12000",
        "--lift",
        "0.1",
        "--earn",
        "1",
        "--point-value",
        "0.01",
        "--breakage",
        "0.25",
        "--interchange",
        "0.02",
    ]
    assert "Break-even spend lift" in run(capsys, *base)
    never = [
        "rewards",
        "--participants",
        "10",
        "--spend",
        "100",
        "--lift",
        "0.1",
        "--earn",
        "3",
        "--point-value",
        "0.01",
        "--interchange",
        "0.015",
    ]
    assert "never" in run(capsys, *never)


def test_pricing(capsys: pytest.CaptureFixture[str]) -> None:
    args = [
        "pricing",
        "--volume",
        "1e7",
        "--mix",
        "debit=0.5:0.002",
        "--mix",
        "credit=0.3:0.003",
        "--mix",
        "commercial=0.2:0.015",
        "--scheme-fee",
        "0.0015",
        "--blended-mdr",
        "0.015",
        "--markup",
        "0.003",
    ]
    out = run(capsys, *args)
    assert "Blended interchange  0.49%" in out
    assert "IC++" in out
    assert (
        main(
            [
                "pricing",
                "--volume",
                "1",
                "--mix",
                "bad",
                "--scheme-fee",
                "0",
                "--blended-mdr",
                "0",
                "--markup",
                "0",
            ]
        )
        == 2
    )
    assert "TYPE=SHARE:RATE" in capsys.readouterr().err


def test_merchant_and_chargebacks(capsys: pytest.CaptureFixture[str]) -> None:
    out = run(
        capsys,
        "merchant",
        "--attempts",
        "100000",
        "--approvals",
        "92000",
        "--sales",
        "4.6e6",
        "--chargebacks",
        "700",
        "--decline",
        "insufficient funds=4000",
    )
    assert "early warning" in out
    assert "insufficient funds" in out
    assert (
        main(
            [
                "merchant",
                "--attempts",
                "1",
                "--approvals",
                "1",
                "--sales",
                "1",
                "--chargebacks",
                "0",
                "--decline",
                "x=y",
            ]
        )
        == 2
    )
    assert "NAME=NUMBER" in capsys.readouterr().err
    out = run(
        capsys,
        "chargebacks",
        "--count",
        "1000",
        "--value",
        "80",
        "--fee",
        "15",
        "--contest-rate",
        "0.6",
        "--win-rate",
        "0.4",
        "--contest-cost",
        "20",
    )
    assert "Recommendation      contest" in out
    out = run(capsys, "chargebacks", "--count", "10", "--value", "10", "--fee", "15")
    assert "accept" in out
