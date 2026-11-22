from typing import Any

import pytest

from cardwise.core.errors import UnknownNameError, ValidationError
from cardwise.credit.model import (
    borrower_from_dict,
    get_industry,
)
from tests.credit_helpers import borrower


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"industry": "space"}, "unknown industry"),
        ({"surprise": 1}, "unknown field"),
        ({"financials": []}, "non-empty list"),
        ({"request.amount": -5}, "request.amount"),
        ({"request.facility_type": "lease"}, "facility_type"),
        ({"request.seniority": "junior"}, "seniority"),
        ({"request.amortisation": 2}, "amortisation"),
        ({"request.refinances": 1e12}, "refinances"),
        ({"collateral": [{"type": "art", "value": 1}]}, "collateral[0].type"),
        ({"collateral": {"type": "cash"}}, "collateral must be a list"),
        ({"qualitative": {"management": 9}}, "1 to 5"),
        ({"kyc_flags": "none"}, "kyc_flags"),
        ({"name": 5}, "name must be text"),
        ({"request": "big"}, "request must be an object"),
    ],
)
def test_bad_borrower_files_are_rejected(change: dict[str, Any], message: str) -> None:
    error = UnknownNameError if message == "unknown industry" else ValidationError
    with pytest.raises(error, match=message.replace("[", r"\[").replace("]", r"\]")):
        borrower_from_dict(borrower(**change))


def test_missing_required_field() -> None:
    data = borrower()
    del data["financials"][0]["ebitda"]
    with pytest.raises(ValidationError, match="ebitda"):
        borrower_from_dict(data)
    with pytest.raises(UnknownNameError):
        get_industry("nope")


def test_optional_borrower_fields_default() -> None:
    data = borrower()
    for key in ("collateral", "qualitative", "kyc_flags", "group", "country"):
        data.pop(key, None)
    b = borrower_from_dict(data)
    assert b.collateral == ()
    assert b.qualitative.management == 3
