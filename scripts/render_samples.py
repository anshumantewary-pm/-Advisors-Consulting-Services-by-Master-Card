"""Regenerate docs/samples/ from the example inputs: python scripts/render_samples.py

tests/test_samples.py fails if the committed samples drift from what the code produces.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cardwise.advisory.diagnose import diagnose  # noqa: E402
from cardwise.advisory.io import review_from_dict  # noqa: E402
from cardwise.advisory.report import render_report  # noqa: E402
from cardwise.advisory.target import target_state  # noqa: E402
from cardwise.credit import borrower_from_dict, decide, render_memo  # noqa: E402


def samples() -> dict[str, str]:
    examples = ROOT / "examples"
    review = review_from_dict(json.loads((examples / "portfolio-review.json").read_text("utf-8")))
    d = diagnose(review)
    borrower = json.loads((examples / "credit" / "northwind-industrial.json").read_text("utf-8"))
    return {
        "portfolio-review-report.md": render_report(d, target_state(d, 0.5)),
        "credit-memo-northwind.md": render_memo(decide(borrower_from_dict(borrower))),
    }


def main() -> None:
    out = ROOT / "docs" / "samples"
    out.mkdir(parents=True, exist_ok=True)
    for name, text in samples().items():
        (out / name).write_text(text, encoding="utf-8")
        print(f"wrote docs/samples/{name}")


if __name__ == "__main__":
    main()
