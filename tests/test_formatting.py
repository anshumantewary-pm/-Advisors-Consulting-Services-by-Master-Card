from cardwise.core.formatting import fmt_bps, fmt_money, fmt_number, fmt_pct, fmt_signed_money


def test_money() -> None:
    assert fmt_money(1234.5) == "$1,234.50"
    assert fmt_money(-2_500_000, compact=True) == "-$2.5M"
    assert fmt_money(999, compact=True) == "$999.00"
    assert fmt_money(3e12, currency="", compact=True) == "3.0T"


def test_other_formats() -> None:
    assert fmt_pct(0.256) == "25.6%"
    assert fmt_number(41666.67) == "41,667"
    assert fmt_signed_money(500) == "+$500.00"
    assert fmt_signed_money(-200) == "-$200.00"
    assert fmt_bps(0.0185) == "185 bp"
    assert fmt_bps(0.00125, 1) == "12.5 bp"
