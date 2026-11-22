"""Render a ``Diagnosis`` as a client-ready Markdown report and a short text summary."""

from __future__ import annotations

from cardwise.advisory.diagnose import Check, Diagnosis
from cardwise.advisory.target import TargetState


def _money(d: Diagnosis, value: float) -> str:
    cur = d.review.currency
    sign = "-" if value < 0 else ""
    m = abs(value)
    for threshold, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if m >= threshold:
            return f"{sign}{cur}{m / threshold:,.1f}{suffix}"
    return f"{sign}{cur}{m:,.0f}"


def _val(c: Check, v: float) -> str:
    if c.unit == "bp":
        return f"{v:.1f} bp"
    return f"{v * 100:.1f}%"


def _table(header: list[str], rows: list[list[str]]) -> list[str]:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    return out + ["| " + " | ".join(r) + " |" for r in rows]


def render_report(d: Diagnosis, target: TargetState | None = None) -> str:
    r, k, p = d.review, d.kpis, d.pnl
    top = d.opportunities[:3]
    lines = [
        f"# Portfolio review: {r.name}",
        "",
        f"**{d.portfolio_type.name}** · health score **{d.health_score}/100** · "
        f"sized opportunity **{_money(d, d.total_opportunity)} a year** (pre-tax)",
        "",
        "## 1. Executive summary",
        "",
    ]
    if top:
        lines.append(
            f"{r.name} earns {_money(d, p.pre_tax_profit)} pre-tax on "
            f"{_money(d, k.receivables)} of receivables (ROA {p.roa * 100:.1f}%). "
            f"{len(d.opportunities)} lever(s) sit outside the typical range. The largest "
            "opportunities are:"
        )
        lines += [""] + [
            f"{i}. **{o.title}**: about {_money(d, o.annual_value)} a year"
            for i, o in enumerate(top, 1)
        ]
    else:
        lines.append(
            f"{r.name} earns {_money(d, p.pre_tax_profit)} pre-tax (ROA {p.roa * 100:.1f}%) and "
            "every KPI checked is within or better than the typical range."
        )
    lines += ["", "## 2. Portfolio at a glance", ""]
    lines += _table(
        ["KPI", "Value"],
        [
            ["Open accounts", f"{k.accounts:,.0f}"],
            ["Active accounts", f"{k.active_accounts:,.0f} ({k.active_rate * 100:.1f}%)"],
            ["Purchase volume", _money(d, k.purchase_volume)],
            ["Spend per active", _money(d, k.spend_per_active)],
            ["Receivables", _money(d, k.receivables)],
            ["Revolve rate", f"{k.revolve_rate * 100:.1f}%"],
            ["Average ticket", "n/a" if k.average_ticket is None else _money(d, k.average_ticket)],
        ],
    )
    lines += ["", "## 3. P&L", ""]
    lines += _table(["Line", "Amount"], [[s.label, _money(d, s.value)] for s in p.steps])
    lines += [
        "",
        f"Revenue mix: interchange {p.revenue_mix['interchange'] * 100:.0f}%, interest "
        f"{p.revenue_mix['interest'] * 100:.0f}%, fees {p.revenue_mix['fees'] * 100:.0f}%. "
        f"Profit per active account {_money(d, p.profit_per_active)}.",
        "",
        "## 4. Benchmarks",
        "",
    ]
    lines += _table(
        ["KPI", "Value", "Typical range", "Status"],
        [
            [
                c.label,
                _val(c, c.value),
                f"{_val(c, c.low)} - {_val(c, c.high)}",
                "**gap**" if c.weak else c.status,
            ]
            for c in d.checks
        ],
    )
    lines += ["", "## 5. Opportunities and levers", ""]
    if not d.opportunities:
        lines.append("No KPI gaps against the typical ranges.")
    for i, o in enumerate(d.opportunities, 1):
        lines += [f"### 5.{i} {o.title} ({_money(d, o.annual_value)} a year)", "", o.detail, ""]
        lines += [f"- {lever}" for lever in o.levers] + [""]
    if target is not None and d.opportunities:
        b = target.bridge
        shares = sorted(set(target.achievement.values()))
        closed = f"{shares[0] * 100:.0f}%" if len(shares) == 1 else "the stated share"
        lines += [
            "## 6. Target state",
            "",
            f"Closing {closed} of each gap together (the P&L is recomputed, so overlapping "
            f"levers are not double-counted) moves pre-tax profit from {_money(d, b.before)} to "
            f"{_money(d, b.after)} and ROA from {target.roa_before * 100:.1f}% to "
            f"{target.roa_after * 100:.1f}%.",
            "",
        ]
        lines += _table(
            ["Driver", "Profit impact"],
            [
                [k.replace("_", " ").capitalize(), _money(d, v)]
                for k, v in b.drivers.items()
                if abs(v) > 0.5
            ],
        )
        lines.append("")
    if d.strengths:
        lines += ["## 7. Strengths", ""] + [f"- {s}" for s in d.strengths] + [""]
    lines += [
        "---",
        "_Ranges are indicative screening benchmarks, not market data for a specific issuer, "
        "market or date. Opportunity values are first-pass, pre-tax estimates of reaching the "
        "edge of each range, and overlap; validate with client data before committing to "
        "targets._",
        "",
    ]
    return "\n".join(lines)


def render_summary(d: Diagnosis) -> str:
    p = d.pnl
    lines = [
        f"{d.review.name} · {d.portfolio_type.name}",
        f"Health score    {d.health_score}/100",
        f"Pre-tax profit  {_money(d, p.pre_tax_profit)} (ROA {p.roa * 100:.2f}%)",
        f"Opportunity     {_money(d, d.total_opportunity)} a year",
        "",
    ]
    for c in d.checks:
        flag = "GAP" if c.weak else c.status
        lines.append(f"  {c.label:<30} {_val(c, c.value):>9}   {flag}")
    if d.opportunities:
        lines += ["", "Top opportunities"]
        lines += [f"  {_money(d, o.annual_value):>9}  {o.title}" for o in d.opportunities]
    return "\n".join(lines)
