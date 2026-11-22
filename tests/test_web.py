"""The web workbench declares its tools as JSON; run each one through the real CLI."""

import json
import re
from pathlib import Path
from typing import Any

import pytest

from cardwise.cli import build_parser

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
TOOLS: list[dict[str, Any]] = json.loads(
    re.search(r'id="tools">(.*?)</script>', PAGE, re.S).group(1)  # type: ignore[union-attr]
)


def argv_for(tool: dict[str, Any]) -> list[str]:
    """Mirror argvFor() in web/index.html."""
    argv = [tool["command"]]
    if tool["kind"] == "file":
        return [*argv, str(ROOT / tool["example"]), *tool.get("args", [])]
    for flag, _label, value, *multi in tool["fields"]:
        if not flag.startswith("--"):
            argv.insert(1, value)
        elif multi:
            for line in value.split("\n"):
                argv += [flag, line]
        else:
            argv += [flag, value]
    return argv


def test_tool_commands_are_unique_and_known() -> None:
    commands = [t["command"] for t in TOOLS]
    assert len(commands) == len(set(commands))
    choices = build_parser()._subparsers._group_actions[0].choices  # type: ignore[union-attr]
    assert set(commands) <= set(choices)


@pytest.mark.parametrize("tool", TOOLS, ids=[t["command"] for t in TOOLS])
def test_every_tool_runs_with_its_defaults(tool: dict[str, Any]) -> None:
    args = build_parser().parse_args(argv_for(tool))
    out = args.handler(args)
    assert out.text
    json.dumps(out.data, default=str)
    if "markdown" in tool:
        assert out.data[tool["markdown"]].startswith("# ")
    for _label, path in tool.get("examples", []):
        assert (ROOT / path).exists()
