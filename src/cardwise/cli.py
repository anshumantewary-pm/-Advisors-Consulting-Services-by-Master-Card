"""Command-line interface: ``cardwise <command> [options] [--json]``.

Each command registers itself with ``@command``: a function that adds its
arguments to a sub-parser and returns the handler. Handlers return an
``Output`` (text to print, data for ``--json``) and never print themselves.
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import io
import json
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from cardwise import __version__
from cardwise.acquiring.chargebacks import chargeback_cost
from cardwise.acquiring.enhanced_data import enhanced_data_savings
from cardwise.acquiring.merchant import merchant_kpis
from cardwise.acquiring.portfolio import Merchant, merchant_portfolio
from cardwise.acquiring.pricing import CardMix, compare_pricing
from cardwise.advisory.diagnose import diagnose
from cardwise.advisory.io import review_from_dict
from cardwise.advisory.report import render_report, render_summary
from cardwise.advisory.target import target_state
from cardwise.benchmark.peers import scorecard
from cardwise.benchmark.ranges import PORTFOLIO_TYPES
from cardwise.core.errors import CardwiseError, ValidationError
from cardwise.core.parse import from_dict
from cardwise.credit import (
    INDUSTRIES,
    borrower_from_dict,
    decide,
    monitor,
    render_memo,
    render_monitoring,
    status_from_dict,
)
from cardwise.credit import render_summary as credit_summary
from cardwise.customer.clv import lifetime_value
from cardwise.customer.cohort import cohort_retention
from cardwise.customer.experiment import sample_size, two_proportion_test
from cardwise.customer.retention import RetentionSegment, retention_plan
from cardwise.customer.rfm import Customer, rfm
from cardwise.issuing.activation import activation_campaign
from cardwise.issuing.line_increase import line_increase
from cardwise.issuing.pnl import CardEconomics, card_pnl
from cardwise.issuing.rewards import rewards_programme
from cardwise.market.sizing import card_market, share_of_wallet
from cardwise.risk.fraud import Scored, best_threshold, rule_economics
from cardwise.risk.provision import provision
from cardwise.risk.rollrate import BUCKETS, analyse
from cardwise.risk.vintage import Vintage, vintage_curves
from cardwise.whatif.distributions import parse_distribution
from cardwise.whatif.goal_seek import goal_seek
from cardwise.whatif.models import MODELS, BuiltinModel, get_model
from cardwise.whatif.montecarlo import render_histogram, simulate
from cardwise.whatif.sensitivity import tornado


@dataclass(frozen=True)
class Output:
    text: str
    data: Any


Handler = Callable[[argparse.Namespace], Output]
Registrar = Callable[[argparse.ArgumentParser], Handler]
_COMMANDS: list[tuple[str, str, Registrar]] = []


def command(name: str, help_text: str) -> Callable[[Registrar], Registrar]:
    def wrap(fn: Registrar) -> Registrar:
        _COMMANDS.append((name, help_text, fn))
        return fn

    return wrap


def read_json(path: str) -> Any:
    try:
        with open(path, encoding="utf-8-sig") as handle:
            return json.load(handle)
    except OSError as error:
        raise ValidationError(f"cannot read {path}: {error.strerror}") from None
    except json.JSONDecodeError as error:
        raise ValidationError(f"{path} is not valid JSON: {error}") from None


def read_text(path: str) -> str:
    try:
        with open(path, encoding="utf-8-sig") as handle:
            return handle.read()
    except OSError as error:
        raise ValidationError(f"cannot read {path}: {error.strerror}") from None


def write_text(path: str, text: str) -> None:
    try:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
    except OSError as error:
        raise ValidationError(f"cannot write {path}: {error.strerror}") from None


def money(value: float) -> str:
    sign = "-" if value < 0 else ""
    m = abs(value)
    for threshold, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if m >= threshold:
            return f"{sign}{m / threshold:,.1f}{suffix}"
    return f"{sign}{m:,.2f}"


def pct(value: float | None, digits: int = 1) -> str:
    return "n/a" if value is None else f"{value * 100:.{digits}f}%"


# ---------------------------------------------------------------- commands
# (each command module section below registers itself)


@command("review", "diagnose a card portfolio against typical ranges and size the opportunities")
def _review(p: argparse.ArgumentParser) -> Handler:
    p.add_argument("file", help="portfolio review JSON (see examples/portfolio-review.json)")
    p.add_argument("--report", metavar="PATH", help="write the Markdown report; '-' prints it")
    p.add_argument(
        "--achievement",
        type=float,
        default=0.5,
        help="share of each gap closed in the target state (default 0.5)",
    )

    def handle(args: argparse.Namespace) -> Output:
        d = diagnose(review_from_dict(read_json(args.file)))
        target = target_state(d, args.achievement)
        md = render_report(d, target)
        text = md if args.report == "-" else render_summary(d)
        if args.report and args.report != "-":
            write_text(args.report, md)
            text += f"\n\nReport written to {args.report}"
        data = d.to_dict()
        data["target_state"] = target.to_dict()
        data["report_markdown"] = md
        return Output(text, data)

    return handle


@command("types", "list portfolio types and the KPI ranges 'review' checks against")
def _types(p: argparse.ArgumentParser) -> Handler:
    def handle(args: argparse.Namespace) -> Output:
        lines = []
        for t in PORTFOLIO_TYPES.values():
            lines.append(f"{t.key:<16} {t.name}")
            for r in t.ranges:
                if r.unit == "bp":
                    band = f"{r.low:g} - {r.high:g} bp"
                else:
                    band = f"{pct(r.low)} - {pct(r.high)}"
                lines.append(f"    {r.label:<32} {band}")
        return Output("\n".join(lines), {k: t.to_dict() for k, t in PORTFOLIO_TYPES.items()})

    return handle


def _add_dataclass_flags(p: argparse.ArgumentParser, cls: type) -> None:
    """One --flag per float field of a dataclass; fields without a default are required."""
    for f in dataclasses.fields(cls):
        required = f.default is dataclasses.MISSING
        hint = "required" if required else f"default {f.default}"
        p.add_argument("--" + f.name.replace("_", "-"), type=float, required=required, help=hint)


@command("pnl", "credit card P&L from volumes and rates")
def _pnl(p: argparse.ArgumentParser) -> Handler:
    _add_dataclass_flags(p, CardEconomics)

    def handle(args: argparse.Namespace) -> Output:
        kwargs = {f.name: getattr(args, f.name) for f in dataclasses.fields(CardEconomics)}
        result = card_pnl(CardEconomics(**{k: v for k, v in kwargs.items() if v is not None}))
        lines = [f"{s.label:<30} {money(s.value):>10}" for s in result.steps]
        lines += [
            "",
            f"Profit per active             {money(result.profit_per_active):>10}",
            f"ROA on receivables            {pct(result.roa, 2):>10}",
        ]
        return Output("\n".join(lines), result.to_dict())

    return handle


@command("rewards", "does a rewards programme pay for itself? ROI and break-even spend lift")
def _rewards(p: argparse.ArgumentParser) -> Handler:
    p.add_argument("--participants", type=float, required=True)
    p.add_argument("--spend", type=float, required=True, help="annual spend per participant")
    p.add_argument("--lift", type=float, required=True, help="expected spend lift, e.g. 0.1")
    p.add_argument("--earn", type=float, required=True, help="points per unit of spend")
    p.add_argument("--point-value", type=float, required=True)
    p.add_argument("--breakage", type=float, default=0.0, help="share of points never redeemed")
    p.add_argument("--interchange", type=float, required=True, help="interchange rate")
    p.add_argument("--network-fee", type=float, default=0.0)
    p.add_argument("--fixed-cost", type=float, default=0.0)

    def handle(args: argparse.Namespace) -> Output:
        r = rewards_programme(
            args.participants,
            args.spend,
            args.lift,
            args.earn,
            args.point_value,
            args.breakage,
            args.interchange,
            args.network_fee,
            args.fixed_cost,
        )
        be = (
            "never (rewards cost exceeds margin)"
            if r.break_even_lift is None
            else pct(r.break_even_lift)
        )
        lines = [
            f"Effective rewards rate  {pct(r.effective_rewards_rate, 2)}",
            f"Incremental spend       {money(r.incremental_spend)}",
            f"Incremental margin      {money(r.incremental_margin)}",
            f"Programme cost          {money(r.programme_cost)}",
            f"Net benefit             {money(r.net_benefit)}",
            f"ROI                     {pct(r.roi)}",
            f"Break-even spend lift   {be}",
        ]
        return Output("\n".join(lines), r.to_dict())

    return handle


def _parse_mix(items: Sequence[str]) -> list[CardMix]:
    mix = []
    for item in items:
        try:
            name, rest = item.split("=", 1)
            share, rate = rest.split(":", 1)
            mix.append(CardMix(name, float(share), float(rate)))
        except ValueError:
            raise ValidationError(f"--mix {item!r} must look like TYPE=SHARE:RATE") from None
    return mix


@command("pricing", "merchant pricing: blended MDR vs interchange++ for a card mix")
def _pricing(p: argparse.ArgumentParser) -> Handler:
    p.add_argument("--volume", type=float, required=True, help="annual card sales")
    p.add_argument(
        "--mix",
        action="append",
        required=True,
        metavar="TYPE=SHARE:RATE",
        help="card type, share of volume and interchange rate; repeat per type",
    )
    p.add_argument("--scheme-fee", type=float, required=True, help="scheme fees as a rate")
    p.add_argument("--blended-mdr", type=float, required=True)
    p.add_argument("--markup", type=float, required=True, help="IC++ acquirer markup as a rate")

    def handle(args: argparse.Namespace) -> Output:
        c = compare_pricing(
            args.volume, _parse_mix(args.mix), args.scheme_fee, args.blended_mdr, args.markup
        )
        rows = [("Blended", c.blended), ("IC++", c.ic_plus_plus)]
        lines = [f"Blended interchange  {pct(c.blended_interchange, 2)}", ""]
        lines.append(f"{'Pricing':<10} {'MDR':>7} {'Merchant cost':>14} {'Acquirer margin':>16}")
        for label, s in rows:
            lines.append(
                f"{label:<10} {pct(s.mdr, 2):>7} {money(s.merchant_cost):>14} "
                f"{money(s.acquirer_margin):>16}"
            )
        lines += [
            "",
            f"Merchant saving on IC++   {money(c.merchant_saving)}",
            f"Markup that keeps margin  {pct(c.equivalent_markup, 2)}",
        ]
        return Output("\n".join(lines), c.to_dict())

    return handle


def _pairs(items: Sequence[str], flag: str) -> dict[str, float]:
    out = {}
    for item in items:
        name, sep, value = item.partition("=")
        try:
            out[name] = float(value)
        except ValueError:
            raise ValidationError(f"{flag} {item!r} must look like NAME=NUMBER") from None
        if not sep:  # pragma: no cover - float("") already raised
            raise ValidationError(f"{flag} {item!r} must look like NAME=NUMBER")
    return out


@command("merchant", "merchant KPIs: approval rate, decline mix, chargeback standing")
def _merchant(p: argparse.ArgumentParser) -> Handler:
    p.add_argument("--attempts", type=float, required=True)
    p.add_argument("--approvals", type=float, required=True)
    p.add_argument("--sales", type=float, required=True, help="approved sales value")
    p.add_argument("--chargebacks", type=float, required=True)
    p.add_argument("--chargeback-value", type=float)
    p.add_argument("--decline", action="append", default=[], metavar="REASON=COUNT")

    def handle(args: argparse.Namespace) -> Output:
        k = merchant_kpis(
            args.attempts,
            args.approvals,
            args.sales,
            args.chargebacks,
            args.chargeback_value,
            _pairs(args.decline, "--decline"),
        )
        lines = [
            f"Approval rate      {pct(k.approval_rate)}",
            f"Average ticket     {money(k.average_ticket)}",
            f"Lost sales value   {money(k.lost_sales_value)}",
            f"Chargeback ratio   {pct(k.chargeback_ratio, 2)} ({k.chargeback_status})",
        ]
        lines += [f"  declines: {r:<22} {pct(s)}" for r, s in k.decline_mix.items()]
        return Output("\n".join(lines), k.to_dict())

    return handle


@command("chargebacks", "chargeback cost and whether contesting them pays")
def _chargebacks(p: argparse.ArgumentParser) -> Handler:
    p.add_argument("--count", type=float, required=True)
    p.add_argument("--value", type=float, required=True, help="average disputed sale value")
    p.add_argument("--fee", type=float, required=True, help="fee per chargeback")
    p.add_argument("--handling", type=float, default=0.0, help="handling cost per chargeback")
    p.add_argument("--contest-rate", type=float, default=0.0)
    p.add_argument("--win-rate", type=float, default=0.0)
    p.add_argument("--contest-cost", type=float, default=0.0)
    p.add_argument("--goods-lost", type=float, default=1.0, help="share of sale value lost")

    def handle(args: argparse.Namespace) -> Output:
        c = chargeback_cost(
            args.count,
            args.value,
            args.fee,
            args.handling,
            args.contest_rate,
            args.win_rate,
            args.contest_cost,
            args.goods_lost,
        )
        verdict = "contest" if c.contest_recommended else "accept (contesting loses money)"
        lines = [
            f"Gross loss          {money(c.gross_loss)}",
            f"Fees and handling   {money(c.fees + c.handling_cost)}",
            f"Recovered           {money(c.recovered)}",
            f"Net loss            {money(c.net_loss)} ({money(c.cost_per_chargeback)} each)",
            f"Recommendation      {verdict}",
        ]
        return Output("\n".join(lines), c.to_dict())

    return handle


@command("fraud", "fraud rule economics from a confusion matrix")
def _fraud(p: argparse.ArgumentParser) -> Handler:
    p.add_argument("--tp", type=float, required=True, help="fraud declined")
    p.add_argument("--fp", type=float, required=True, help="good transactions declined")
    p.add_argument("--fn", type=float, required=True, help="fraud approved")
    p.add_argument("--tn", type=float, required=True, help="good transactions approved")
    p.add_argument("--fraud-value", type=float, required=True, help="average fraud amount")
    p.add_argument("--good-value", type=float, required=True, help="average good amount")
    p.add_argument("--margin", type=float, required=True, help="margin on a good sale")
    p.add_argument("--churn-cost", type=float, default=0.0, help="per good customer declined")

    def handle(args: argparse.Namespace) -> Output:
        r = rule_economics(
            args.tp,
            args.fp,
            args.fn,
            args.tn,
            args.fraud_value,
            args.good_value,
            args.margin,
            args.churn_cost,
        )
        fpr = "n/a" if r.false_positive_ratio is None else f"{r.false_positive_ratio:.1f} : 1"
        lines = [
            f"Precision          {pct(r.precision)}",
            f"Recall             {pct(r.recall)}",
            f"Decline rate       {pct(r.decline_rate, 2)}",
            f"Good : fraud declined  {fpr}",
            f"Fraud prevented    {money(r.fraud_prevented)}",
            f"Fraud missed       {money(r.fraud_missed)}",
            f"Insult cost        {money(r.insult_cost)}",
            f"Total cost         {money(r.total_cost)}",
        ]
        return Output("\n".join(lines), r.to_dict())

    return handle


@command("threshold", "cost-optimal fraud score cut-off from scored transactions (CSV)")
def _threshold(p: argparse.ArgumentParser) -> Handler:
    p.add_argument("file", help="CSV with columns score,is_fraud,value")
    p.add_argument("--margin", type=float, required=True, help="margin on a good sale")
    p.add_argument("--churn-cost", type=float, default=0.0)

    def handle(args: argparse.Namespace) -> Output:
        rows = []
        reader = csv.DictReader(io.StringIO(read_text(args.file)))
        for i, row in enumerate(reader, start=2):
            try:
                rows.append(
                    Scored(
                        float(row["score"]),
                        row["is_fraud"].strip() in ("1", "true"),
                        float(row["value"]),
                    )
                )
            except (KeyError, ValueError, AttributeError):
                raise ValidationError(f"{args.file} line {i}: need score,is_fraud,value") from None
        c = best_threshold(rows, args.margin, args.churn_cost)
        lines = [
            f"Best threshold   decline when score >= {c.threshold:g}",
            f"Total cost       {money(c.total_cost)}",
            f"Fraud missed     {money(c.fraud_missed)}",
            f"Insult cost      {money(c.insult_cost)}",
            f"Decline rate     {pct(c.decline_rate, 2)}",
            f"Fraud caught     {pct(c.recall)} of cases",
        ]
        data = c.to_dict()
        data["threshold"] = None if c.threshold == float("inf") else c.threshold
        data["curve"] = [(None if t == float("inf") else t, v) for t, v in c.curve]
        return Output("\n".join(lines), data)

    return handle


@command("rollrate", "delinquency roll rates, flow-through and projected charge-offs (JSON)")
def _rollrate(p: argparse.ArgumentParser) -> Handler:
    p.add_argument("file", help="JSON with moves, balances and months (examples/roll-rates.json)")

    def handle(args: argparse.Namespace) -> Output:
        body = read_json(args.file)
        if not isinstance(body, dict) or "moves" not in body or "balances" not in body:
            raise ValidationError(f"{args.file} needs 'moves' and 'balances'")
        months = body.get("months", 12)
        if isinstance(months, bool) or not isinstance(months, int):
            raise ValidationError("months must be a whole number")
        a = analyse(body["moves"], body["balances"], months)
        lines = ["Forward roll rates"]
        lines += [f"  {b:<8} -> next  {pct(r)}" for b, r in a.roll_rates.items()]
        lines += [
            "",
            f"Flow-through to charge-off   {pct(a.flow_through, 3)}",
            f"Charge-offs over {months} months  {money(a.projected_charge_offs)}",
            f"Loss rate on balances        {pct(a.loss_rate, 2)}",
            "",
            "Balances at month " + str(months),
        ]
        lines += [f"  {b:<10} {money(a.projection[-1][b]):>10}" for b in BUCKETS]
        return Output("\n".join(lines), a.to_dict())

    return handle


@command("vintage", "loss vintage curves: compare cohorts at the same months on book (JSON)")
def _vintage(p: argparse.ArgumentParser) -> Handler:
    p.add_argument("file", help="JSON with a list of vintages (examples/vintages.json)")
    p.add_argument("--at-month", type=int, help="months on book to compare (default: shortest)")

    def handle(args: argparse.Namespace) -> Output:
        body = read_json(args.file)
        raw = body.get("vintages") if isinstance(body, dict) else None
        if not isinstance(raw, list):
            raise ValidationError(f"{args.file} needs a 'vintages' list")
        try:
            vintages = [
                Vintage(
                    v["name"], float(v["originated"]), tuple(float(x) for x in v["monthly_losses"])
                )
                for v in raw
            ]
        except (KeyError, TypeError, ValueError):
            raise ValidationError("each vintage needs name, originated, monthly_losses") from None
        vc = vintage_curves(vintages, args.at_month)
        lines = [f"Cumulative loss rate at month {vc.at_month}"]
        lines += [f"  {k:<10} {pct(v, 2)}" for k, v in vc.loss_at_month.items()]
        lines += ["", f"Best {vc.best} · worst {vc.worst}"]
        return Output("\n".join(lines), vc.to_dict())

    return handle


def _csv_rows(path: str, columns: Sequence[str]) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(read_text(path)))
    missing = [c for c in columns if c not in (reader.fieldnames or [])]
    if missing:
        raise ValidationError(f"{path} is missing column(s): {', '.join(missing)}")
    return list(reader)


@command("rfm", "RFM segmentation of a customer file (CSV)")
def _rfm(p: argparse.ArgumentParser) -> Handler:
    p.add_argument("file", help="CSV with id,days_since_last,transactions,spend")

    def handle(args: argparse.Namespace) -> Output:
        rows = _csv_rows(args.file, ("id", "days_since_last", "transactions", "spend"))
        try:
            customers = [
                Customer(
                    r["id"],
                    float(r["days_since_last"]),
                    float(r["transactions"]),
                    float(r["spend"]),
                )
                for r in rows
            ]
        except ValueError as error:
            raise ValidationError(f"{args.file}: {error}") from None
        res = rfm(customers)
        total = sum(res.segment_spend.values()) or 1.0
        lines = [f"{'Segment':<18} {'Customers':>9} {'Spend share':>12}"]
        for name, count in sorted(res.segment_counts.items(), key=lambda kv: -kv[1]):
            lines.append(f"{name:<18} {count:>9} {pct(res.segment_spend[name] / total):>12}")
        return Output("\n".join(lines), res.to_dict())

    return handle


@command("cohort", "cohort retention table from activity rows (CSV)")
def _cohort(p: argparse.ArgumentParser) -> Handler:
    p.add_argument("file", help="CSV with customer_id,cohort,active_period (integers)")

    def handle(args: argparse.Namespace) -> Output:
        rows = _csv_rows(args.file, ("customer_id", "cohort", "active_period"))
        try:
            activity = [(r["customer_id"], int(r["cohort"]), int(r["active_period"])) for r in rows]
        except ValueError as error:
            raise ValidationError(f"{args.file}: {error}") from None
        t = cohort_retention(activity)
        lines = ["Cohort  Size  " + "  ".join(f"P{k:<4}" for k in range(len(t.average)))]
        for c in t.cohorts:
            cells = "  ".join(f"{v * 100:4.0f}%" for v in t.retention[c])
            lines.append(f"{c:<6} {t.sizes[c]:>5}  {cells}")
        lines.append("Avg          " + "  ".join(f"{v * 100:4.0f}%" for v in t.average))
        return Output("\n".join(lines), t.to_dict())

    return handle


@command("clv", "customer lifetime value and the most you should pay to acquire one")
def _clv(p: argparse.ArgumentParser) -> Handler:
    p.add_argument("--margin", type=float, required=True, help="annual margin per customer")
    p.add_argument("--retention", type=float, required=True, help="annual retention, 0..1")
    p.add_argument("--discount-rate", type=float, default=0.10)
    p.add_argument("--ltv-cac", type=float, default=3.0, help="target LTV:CAC ratio")

    def handle(args: argparse.Namespace) -> Output:
        v = lifetime_value(args.margin, args.retention, args.discount_rate, args.ltv_cac)
        lines = [
            f"Expected lifetime     {v.expected_lifetime_years:.1f} years",
            f"Lifetime value        {money(v.clv)}",
            f"Max acquisition cost  {money(v.max_acquisition_cost)} (at {args.ltv_cac:g}:1)",
        ]
        data = v.to_dict()
        for k in ("expected_lifetime_years", "clv", "max_acquisition_cost"):
            if data[k] == float("inf"):
                data[k] = None
        return Output("\n".join(lines), data)

    return handle


@command("experiment", "read a campaign test vs control: lift, significance, value")
def _experiment(p: argparse.ArgumentParser) -> Handler:
    p.add_argument("--test", required=True, metavar="SIZE,CONVERSIONS")
    p.add_argument("--control", required=True, metavar="SIZE,CONVERSIONS")
    p.add_argument("--confidence", type=float, default=0.95)
    p.add_argument("--value", type=float, default=0.0, help="value per extra conversion")

    def handle(args: argparse.Namespace) -> Output:
        def pair(text: str, flag: str) -> tuple[float, float]:
            try:
                a, b = (float(x) for x in text.split(","))
            except ValueError:
                raise ValidationError(f"{flag} must look like SIZE,CONVERSIONS") from None
            return a, b

        (nt, xt), (nc, xc) = pair(args.test, "--test"), pair(args.control, "--control")
        r = two_proportion_test(nt, xt, nc, xc, args.confidence, args.value)
        verdict = "significant" if r.significant else "not significant"
        lines = [
            f"Test rate        {pct(r.test_rate, 2)}",
            f"Control rate     {pct(r.control_rate, 2)}",
            f"Lift             {pct(r.absolute_lift, 2)} ({pct(r.relative_lift)} relative)",
            f"{args.confidence:.0%} CI         {pct(r.ci_low, 2)} to {pct(r.ci_high, 2)}",
            f"p-value          {r.p_value:.4f} ({verdict})",
            f"Extra responders {r.incremental_responders:,.0f}",
            f"Extra value      {money(r.incremental_value)}",
        ]
        return Output("\n".join(lines), r.to_dict())

    return handle


@command("sample-size", "customers needed per group to detect a lift")
def _sample_size(p: argparse.ArgumentParser) -> Handler:
    p.add_argument("--baseline", type=float, required=True, help="control response rate")
    p.add_argument("--lift", type=float, required=True, help="smallest absolute lift to detect")
    p.add_argument("--confidence", type=float, default=0.95)
    p.add_argument("--power", type=float, default=0.8)

    def handle(args: argparse.Namespace) -> Output:
        n = sample_size(args.baseline, args.lift, args.confidence, args.power)
        text = f"{n:,} customers per group ({2 * n:,} in total)"
        return Output(text, {"per_group": n, "total": 2 * n})

    return handle


@command("market", "card market size, cash displacement and revenue pool")
def _market(p: argparse.ArgumentParser) -> Handler:
    p.add_argument("--population", type=float, required=True)
    p.add_argument("--spend-per-capita", type=float, required=True)
    p.add_argument("--card-share", type=float, required=True, help="card share of spend today")
    p.add_argument("--growth", type=float, required=True, help="annual consumer spend growth")
    p.add_argument("--target-share", type=float, required=True, help="card share after --years")
    p.add_argument("--years", type=int, default=5)
    p.add_argument("--revenue-yield", type=float, required=True, help="revenue per unit of spend")

    def handle(args: argparse.Namespace) -> Output:
        m = card_market(
            args.population,
            args.spend_per_capita,
            args.card_share,
            args.growth,
            args.target_share,
            args.years,
            args.revenue_yield,
        )
        lines = [
            f"{s.label:<40} {pct(s.value) if s.unit == '%' else money(s.value):>10}"
            for s in m.steps
        ]
        return Output("\n".join(lines), m.to_dict())

    return handle


@command("wallet", "share of wallet and the spend opportunity at a target share")
def _wallet(p: argparse.ArgumentParser) -> Handler:
    p.add_argument("--our-spend", type=float, required=True)
    p.add_argument("--total-spend", type=float, required=True, help="all card spend of customers")
    p.add_argument("--target", type=float, required=True, help="target share of wallet")
    p.add_argument("--main-card-customers", type=float)
    p.add_argument("--customers", type=float)

    def handle(args: argparse.Namespace) -> Output:
        w = share_of_wallet(
            args.our_spend, args.total_spend, args.target, args.main_card_customers, args.customers
        )
        lines = [
            f"Share of wallet    {pct(w.share_of_wallet)}",
            f"Top of wallet      {pct(w.top_of_wallet_rate)}",
            f"Opportunity        {money(w.opportunity_at_target)} at {pct(args.target)}",
        ]
        return Output("\n".join(lines), w.to_dict())

    return handle


@command("benchmark", "rank a client against a peer set on every shared KPI (JSON)")
def _benchmark(p: argparse.ArgumentParser) -> Handler:
    p.add_argument("file", help="JSON with client, peers, higher_is_better")

    def handle(args: argparse.Namespace) -> Output:
        body = read_json(args.file)
        if not isinstance(body, dict) or "client" not in body or "peers" not in body:
            raise ValidationError(f"{args.file} needs 'client' and 'peers'")
        rows = scorecard(body["client"], body["peers"], body.get("higher_is_better", {}))
        lines = [f"{'KPI':<24} {'Client':>10} {'Median':>10} {'Rank':>6} {'Quartile':>9}"]
        for r in rows:
            lines.append(
                f"{r.metric:<24} {r.value:>10.4g} {r.median:>10.4g} "
                f"{r.percentile_rank * 100:>5.0f}% {'Q' + str(r.quartile):>9}"
            )
        return Output("\n".join(lines), [r.to_dict() for r in rows])

    return handle


@command("credit", "CreditDecision: borrower file in, lending decision and credit memo out")
def _credit(p: argparse.ArgumentParser) -> Handler:
    p.add_argument("file", help="borrower JSON (see examples/credit/)")
    p.add_argument("--memo", metavar="PATH", help="write the credit memo (Markdown); '-' prints it")

    def handle(args: argparse.Namespace) -> Output:
        decision = decide(borrower_from_dict(read_json(args.file)))
        memo = render_memo(decision)
        text = memo if args.memo == "-" else credit_summary(decision)
        if args.memo and args.memo != "-":
            write_text(args.memo, memo)
            text += f"\n\nCredit memo written to {args.memo}"
        data = decision.to_dict()
        data["memo_markdown"] = memo
        return Output(text, data)

    return handle


@command("collect", "monitor a live facility: early warnings, staging, workout plan")
def _collect(p: argparse.ArgumentParser) -> Handler:
    p.add_argument("file", help="facility status JSON (see examples/credit/)")

    def handle(args: argparse.Namespace) -> Output:
        result = monitor(status_from_dict(read_json(args.file)))
        return Output(render_monitoring(result), result.to_dict())

    return handle


@command("industries", "list industries and leverage ceilings used by 'credit'")
def _industries(p: argparse.ArgumentParser) -> Handler:
    def handle(args: argparse.Namespace) -> Output:
        lines = [
            f"{i.key:<18} {i.name:<38} risk {i.risk}/5  max leverage {i.max_leverage:.1f}x"
            for i in INDUSTRIES.values()
        ]
        return Output("\n".join(lines), {k: i.to_dict() for k, i in INDUSTRIES.items()})

    return handle


def _split(item: str, flag: str) -> tuple[str, str]:
    name, sep, value = item.partition("=")
    if not sep or not name:
        raise ValidationError(f"{flag} {item!r} must look like NAME=VALUE")
    return name, value


def _base(m: BuiltinModel, overrides: Sequence[str]) -> dict[str, float]:
    base = dict(m.defaults)
    for item in overrides:
        name, value = _split(item, "--set")
        if name not in base:
            raise ValidationError(f"model {m.name!r} has no input {name!r}")
        try:
            base[name] = float(value)
        except ValueError:
            raise ValidationError(f"--set {item!r}: {value!r} is not a number") from None
    return base


def _bracket(text: str, flag: str) -> tuple[float, float]:
    try:
        low, high = (float(x) for x in text.split(":"))
    except ValueError:
        raise ValidationError(f"{flag} must look like LOW:HIGH") from None
    return low, high


@command("models", "list built-in what-if models and their default inputs")
def _models(p: argparse.ArgumentParser) -> Handler:
    def handle(args: argparse.Namespace) -> Output:
        lines = []
        for m in MODELS.values():
            lines.append(f"{m.name:<10} {m.description} (output: {m.output})")
            lines += [f"    {k} = {v:,.10g}" for k, v in m.defaults.items()]
        data = {
            k: {"description": m.description, "defaults": dict(m.defaults)}
            for k, m in MODELS.items()
        }
        return Output("\n".join(lines), data)

    return handle


def _model_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("model", choices=list(MODELS), help="built-in model (see 'models')")
    p.add_argument("--set", action="append", default=[], metavar="NAME=VALUE")


@command("sensitivity", "tornado: which inputs move a model's output most")
def _sensitivity(p: argparse.ArgumentParser) -> Handler:
    _model_args(p)
    p.add_argument("--range", action="append", default=[], metavar="NAME=LOW:HIGH")
    p.add_argument("--pct", type=float, default=0.10, help="swing when no --range (default 0.1)")

    def handle(args: argparse.Namespace) -> Output:
        m = get_model(args.model)
        base = _base(m, args.set)
        ranges = {}
        for item in args.range:
            name, value = _split(item, "--range")
            ranges[name] = _bracket(value, "--range")
        t = tornado(m.fn, base, ranges or None, args.pct)
        lines = [f"Base {m.output}: {money(t.base_output)}", ""]
        for b in t.bars:
            lines.append(
                f"{b.input:<24} {money(b.output_at_low):>10} .. "
                f"{money(b.output_at_high):>10}   swing {money(b.swing)}"
            )
        data = t.to_dict()
        data["most_sensitive"] = t.most_sensitive
        return Output("\n".join(lines), data)

    return handle


@command("goalseek", "find the input value that makes a model hit a target")
def _goalseek(p: argparse.ArgumentParser) -> Handler:
    _model_args(p)
    p.add_argument("--vary", required=True, metavar="NAME")
    p.add_argument("--target", type=float, default=0.0)
    p.add_argument("--between", required=True, metavar="LOW:HIGH")

    def handle(args: argparse.Namespace) -> Output:
        m = get_model(args.model)
        low, high = _bracket(args.between, "--between")
        g = goal_seek(m.fn, _base(m, args.set), args.vary, args.target, low, high)
        text = f"{g.input} = {g.value:,.6g} gives {m.output} {money(g.output)}"
        return Output(text, g.to_dict())

    return handle


@command("simulate", "Monte Carlo: uncertain inputs give a range of outcomes")
def _simulate(p: argparse.ArgumentParser) -> Handler:
    _model_args(p)
    p.add_argument(
        "--dist",
        action="append",
        default=[],
        metavar="NAME=SPEC",
        help="e.g. net_credit_loss_rate=tri:0.03:0.035:0.06",
    )
    p.add_argument("--runs", type=int, default=10_000)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--threshold", type=float, default=0.0)

    def handle(args: argparse.Namespace) -> Output:
        m = get_model(args.model)
        inputs: dict[str, object] = dict(_base(m, args.set))
        for item in args.dist:
            name, spec = _split(item, "--dist")
            if name not in inputs:
                raise ValidationError(f"model {m.name!r} has no input {name!r}")
            inputs[name] = parse_distribution(spec)
        s = simulate(m.fn, inputs, args.runs, args.seed, args.threshold)  # type: ignore[arg-type]
        lines = [
            f"Mean {m.output}     {money(s.mean)}",
            f"90% band          {money(s.band_90[0])} to {money(s.band_90[1])}",
            f"P(< {args.threshold:g})        {pct(s.prob_below_threshold)}",
            "",
            *render_histogram(s.histogram),
        ]
        return Output("\n".join(lines), s.to_dict())

    return handle


@command("activation", "is an activation campaign worth it? incremental actives, NPV, payback")
def _activation(p: argparse.ArgumentParser) -> Handler:
    p.add_argument("--targeted", type=float, required=True, help="dormant accounts contacted")
    p.add_argument("--response", type=float, required=True, help="activation rate if targeted")
    p.add_argument("--control", type=float, default=0.0, help="activation rate if not targeted")
    p.add_argument("--contact-cost", type=float, default=0.0, help="per account contacted")
    p.add_argument("--incentive", type=float, default=0.0, help="per account that activates")
    p.add_argument("--profit", type=float, required=True, help="annual profit of an active")
    p.add_argument("--retention", type=float, default=0.8, help="share still active each year")
    p.add_argument("--discount-rate", type=float, default=0.10)
    p.add_argument("--years", type=int, default=3)

    def handle(args: argparse.Namespace) -> Output:
        c = activation_campaign(
            args.targeted,
            args.response,
            args.control,
            args.contact_cost,
            args.incentive,
            args.profit,
            args.retention,
            args.discount_rate,
            args.years,
        )
        cpi = "n/a" if c.cost_per_incremental is None else money(c.cost_per_incremental)
        payback = "not within horizon" if c.payback_years is None else f"year {c.payback_years:g}"
        lines = [
            f"Incremental activations  {c.incremental_activations:,.0f}",
            f"Campaign cost            {money(c.campaign_cost)} ({cpi} per incremental active)",
            f"Value per new active     {money(c.value_per_active)} over {args.years} years",
            f"Net value                {money(c.net_value)} (ROI {pct(c.roi)})",
            f"Payback                  {payback}",
        ]
        return Output("\n".join(lines), c.to_dict())

    return handle


@command("retention", "which at-risk segments are worth a retention offer? (JSON)")
def _retention(p: argparse.ArgumentParser) -> Handler:
    p.add_argument("file", help="JSON with a 'segments' list (examples/retention-segments.json)")

    def handle(args: argparse.Namespace) -> Output:
        body = read_json(args.file)
        raw = body.get("segments") if isinstance(body, dict) else None
        if not isinstance(raw, list):
            raise ValidationError(f"{args.file} needs a 'segments' list")
        segments = [from_dict(RetentionSegment, s, f"segments[{i}]") for i, s in enumerate(raw)]
        plan = retention_plan(segments)
        lines = [f"{'Segment':<28} {'Value/customer':>14} {'Total':>10}  Offer?"]
        for d in plan.decisions:
            lines.append(
                f"{d.name:<28} {money(d.value_per_customer):>14} "
                f"{money(d.total_value):>10}  {'yes' if d.target else 'no'}"
            )
        lines += [
            "",
            f"Target {plan.customers_targeted:,.0f} customers, budget {money(plan.budget)}, "
            f"expected value {money(plan.expected_value)}, about "
            f"{plan.customers_saved:,.0f} customers kept",
        ]
        return Output("\n".join(lines), plan.to_dict())

    return handle


@command("merchants", "merchant portfolio profitability and repricing (JSON)")
def _merchants(p: argparse.ArgumentParser) -> Handler:
    p.add_argument("file", help="JSON with merchants and target_bps (see examples/)")

    def handle(args: argparse.Namespace) -> Output:
        body = read_json(args.file)
        raw = body.get("merchants") if isinstance(body, dict) else None
        if not isinstance(raw, list):
            raise ValidationError(f"{args.file} needs a 'merchants' list")
        merchants = [from_dict(Merchant, m, f"merchants[{i}]") for i, m in enumerate(raw)]
        target = body.get("target_bps", 0.0)
        if isinstance(target, bool) or not isinstance(target, (int, float)):
            raise ValidationError("target_bps must be a number")
        pf = merchant_portfolio(merchants, float(target))
        lines = [f"{'Merchant':<18} {'Volume':>9} {'Contribution':>13} {'bp':>6}  Reprice to"]
        for m in pf.merchants:
            rep = "" if m.repriced_mdr is None else pct(m.repriced_mdr, 2)
            lines.append(
                f"{m.name:<18} {money(m.volume):>9} {money(m.contribution):>13} "
                f"{m.contribution_bps:>6.1f}  {rep}"
            )
        lines += [
            "",
            f"Total contribution  {money(pf.total_contribution)} on {money(pf.total_volume)}",
            f"Loss makers         {', '.join(pf.loss_makers) or 'none'}",
            f"Repricing uplift    {money(pf.repricing_uplift)} (to {float(target):g} bp)",
            f"Top-5 concentration {pct(pf.concentration_top5)}",
        ]
        return Output("\n".join(lines), pf.to_dict())

    return handle


@command("provision", "card loss provisions: IFRS 9 stages and lifetime view (JSON)")
def _provision(p: argparse.ArgumentParser) -> Handler:
    p.add_argument("file", help="JSON with balances, pd_12m, lgd (examples/provision.json)")

    def handle(args: argparse.Namespace) -> Output:
        body = read_json(args.file)
        if not isinstance(body, dict) or not {"balances", "pd_12m", "lgd"} <= set(body):
            raise ValidationError(f"{args.file} needs balances, pd_12m and lgd")
        pv = provision(
            body["balances"], body["pd_12m"], body["lgd"], body.get("lifetime_years", 2.5)
        )
        lines = [f"{'Stage':<8} {'Balances':>10} {'ECL':>10} {'Coverage':>9}"]
        for s in ("stage 1", "stage 2", "stage 3"):
            bal, ecl = pv.stage_balances[s], pv.stage_ecl[s]
            cov = pct(ecl / bal) if bal else "n/a"
            lines.append(f"{s:<8} {money(bal):>10} {money(ecl):>10} {cov:>9}")
        lines += [
            "",
            f"IFRS 9 ECL        {money(pv.ifrs9_ecl)} ({pct(pv.coverage, 2)} of balances)",
            f"Lifetime (CECL)   {money(pv.lifetime_ecl)} ({pct(pv.lifetime_coverage, 2)})",
        ]
        return Output("\n".join(lines), pv.to_dict())

    return handle


EXAMPLES: tuple[tuple[str, str], ...] = (
    (
        "examples/portfolio-review.json",
        "cardwise review examples/portfolio-review.json --report report.md",
    ),
    ("examples/peer-benchmark.json", "cardwise benchmark examples/peer-benchmark.json"),
    ("examples/merchant-portfolio.json", "cardwise merchants examples/merchant-portfolio.json"),
    (
        "examples/scored-transactions.csv",
        "cardwise threshold examples/scored-transactions.csv --margin 0.05",
    ),
    ("examples/roll-rates.json", "cardwise rollrate examples/roll-rates.json"),
    ("examples/vintages.json", "cardwise vintage examples/vintages.json"),
    ("examples/provision.json", "cardwise provision examples/provision.json"),
    ("examples/customers.csv", "cardwise rfm examples/customers.csv"),
    ("examples/activity.csv", "cardwise cohort examples/activity.csv"),
    ("examples/retention-segments.json", "cardwise retention examples/retention-segments.json"),
    (
        "examples/credit/northwind-industrial.json",
        "cardwise credit examples/credit/northwind-industrial.json --memo memo.md",
    ),
    (
        "examples/credit/coastal-retail-q3-review.json",
        "cardwise collect examples/credit/coastal-retail-q3-review.json",
    ),
)


@command("examples", "list the example files and the command that runs each one")
def _examples(p: argparse.ArgumentParser) -> Handler:
    def handle(args: argparse.Namespace) -> Output:
        lines = ["Run these from the repository root:", ""]
        lines += [f"  {cmd}" for _, cmd in EXAMPLES]
        return Output("\n".join(lines), [{"file": f, "command": c} for f, c in EXAMPLES])

    return handle


@command("line-increase", "credit line increase economics: profit and break-even loss rate")
def _line_increase(p: argparse.ArgumentParser) -> Handler:
    p.add_argument("--accounts", type=float, required=True, help="accounts given an increase")
    p.add_argument("--increase", type=float, required=True, help="extra limit per account")
    p.add_argument("--utilisation", type=float, required=True, help="share of new limit drawn")
    p.add_argument("--revolve-share", type=float, required=True, help="share that pays interest")
    p.add_argument("--apr", type=float, required=True)
    p.add_argument("--cost-of-funds", type=float, required=True)
    p.add_argument("--loss-rate", type=float, required=True, help="loss rate on new balances")
    p.add_argument("--existing-balance", type=float, default=0.0, help="per account")
    p.add_argument("--loss-uplift", type=float, default=0.0, help="on existing balances")
    p.add_argument("--extra-spend", type=float, default=0.0, help="per account per year")
    p.add_argument("--interchange", type=float, default=0.0)

    def handle(args: argparse.Namespace) -> Output:
        r = line_increase(
            args.accounts,
            args.increase,
            args.utilisation,
            args.revolve_share,
            args.apr,
            args.cost_of_funds,
            args.loss_rate,
            args.existing_balance,
            args.loss_uplift,
            args.extra_spend,
            args.interchange,
        )
        lines = [f"{s.label:<38} {money(s.value):>10}" for s in r.steps]
        lines += [
            "",
            f"New balances                           {money(r.new_balances):>10}",
            f"Profit per account                     {money(r.profit_per_account):>10}",
            f"Break-even loss rate on new balances   {pct(r.break_even_loss_rate, 2):>10}",
        ]
        return Output("\n".join(lines), r.to_dict())

    return handle


@command("enhanced-data", "interchange saving from passing Level 2/3 data on commercial cards")
def _enhanced_data(p: argparse.ArgumentParser) -> Handler:
    p.add_argument("--volume", type=float, required=True, help="annual commercial card volume")
    p.add_argument("--standard-rate", type=float, required=True)
    p.add_argument("--level2-rate", type=float, required=True)
    p.add_argument("--level3-rate", type=float, required=True)
    p.add_argument("--l2-today", type=float, default=0.0, help="share qualifying for L2 today")
    p.add_argument("--l3-today", type=float, default=0.0)
    p.add_argument("--l2-after", type=float, required=True, help="share qualifying after")
    p.add_argument("--l3-after", type=float, required=True)
    p.add_argument("--implementation-cost", type=float, default=0.0)

    def handle(args: argparse.Namespace) -> Output:
        s = enhanced_data_savings(
            args.volume,
            args.standard_rate,
            args.level2_rate,
            args.level3_rate,
            args.l2_today,
            args.l3_today,
            args.l2_after,
            args.l3_after,
            args.implementation_cost,
        )
        payback = "n/a" if s.payback_months is None else f"{s.payback_months:.1f} months"
        lines = [
            f"Effective rate today   {pct(s.effective_rate_today, 3)}",
            f"Effective rate after   {pct(s.effective_rate_after, 3)}",
            f"Annual saving          {money(s.annual_saving)}",
            f"Payback                {payback}",
        ]
        return Output("\n".join(lines), s.to_dict())

    return handle


# ---------------------------------------------------------------- end of commands


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cardwise",
        description="Payments and banking advisory analytics.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="print machine-readable JSON")
    sub = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")
    for name, help_text, register in _COMMANDS:
        p = sub.add_parser(name, parents=[common], help=help_text, description=help_text)
        p.set_defaults(handler=register(p))
    return parser


def ensure_utf8(stream: object) -> None:
    """Windows pipes default to cp1252; switch to UTF-8 so symbols print."""
    if isinstance(stream, io.TextIOWrapper) and (stream.encoding or "").lower() not in (
        "utf-8",
        "utf8",
    ):
        stream.reconfigure(encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    ensure_utf8(sys.stdout)
    args = build_parser().parse_args(argv)
    try:
        output: Output = args.handler(args)
    except CardwiseError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(output.data, indent=2, allow_nan=False, default=str))
    else:
        print(output.text)
    return 0
