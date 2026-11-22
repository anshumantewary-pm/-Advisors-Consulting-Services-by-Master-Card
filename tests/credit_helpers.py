import copy
import json
from pathlib import Path
from typing import Any

from cardwise.credit.model import Financials

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "credit"


def load(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((EXAMPLES / f"{name}.json").read_text(encoding="utf-8"))
    return data


def fin(**overrides: Any) -> Financials:
    base: dict[str, Any] = {
        "period": "FY",
        "revenue": 100e6,
        "ebitda": 20e6,
        "interest_expense": 2e6,
        "total_debt": 40e6,
        "cash": 5e6,
        "capex": 4e6,
        "taxes": 2e6,
        "scheduled_principal": 4e6,
    }
    base.update(overrides)
    return Financials(**base)


def borrower(**changes: Any) -> dict[str, Any]:
    data = copy.deepcopy(load("northwind-industrial"))
    for key, value in changes.items():
        if key.startswith("request."):
            data["request"][key.split(".", 1)[1]] = value
        else:
            data[key] = value
    return data


def status(**changes: Any) -> dict[str, Any]:
    data = copy.deepcopy(load("coastal-retail-q3-review"))
    data.update(changes)
    return data
