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
from cardwise.acquiring.merchant import merchant_kpis
from cardwise.acquiring.pricing import CardMix, compare_pricing
from cardwise.advisory.diagnose import diagnose
from cardwise.advisory.io import review_from_dict
from cardwise.advisory.report import render_report, render_summary
from cardwise.benchmark.ranges import PORTFOLIO_TYPES
from cardwise.core.errors import CardwiseError, ValidationError
from cardwise.issuing.pnl import CardEconomics, card_pnl
from cardwise.issuing.rewards import rewards_programme
from cardwise.risk.fraud import Scored, best_threshold, rule_economics
from cardwise.risk.rollrate import BUCKETS, analyse
from cardwise.risk.vintage import Vintage, vintage_curves


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

    def handle(args: argparse.Namespace) -> Output:
        d = diagnose(review_from_dict(read_json(args.file)))
        md = render_report(d)
        text = md if args.report == "-" else render_summary(d)
        if args.report and args.report != "-":
            write_text(args.report, md)
            text += f"\n\nReport written to {args.report}"
        data = d.to_dict()
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
