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
