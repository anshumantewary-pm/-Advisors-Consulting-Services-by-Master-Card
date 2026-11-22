"""Command-line interface: ``cardwise <command> [options] [--json]``.

Each command registers itself with ``@command``: a function that adds its
arguments to a sub-parser and returns the handler. Handlers return an
``Output`` (text to print, data for ``--json``) and never print themselves.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from cardwise import __version__
from cardwise.advisory.diagnose import diagnose
from cardwise.advisory.io import review_from_dict
from cardwise.advisory.report import render_report, render_summary
from cardwise.benchmark.ranges import PORTFOLIO_TYPES
from cardwise.core.errors import CardwiseError, ValidationError


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
