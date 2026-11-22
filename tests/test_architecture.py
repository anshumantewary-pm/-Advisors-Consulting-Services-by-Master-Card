"""Enforce the layering in docs/ARCHITECTURE.md: each package imports only what it may."""

import ast
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[1] / "src" / "cardwise"

DOMAINS = {"issuing", "acquiring", "risk", "customer", "market", "benchmark", "credit"}
ALLOWED: dict[str, set[str]] = {
    "core": {"core"},
    **{d: {"core", d} for d in DOMAINS},
    "advisory": {"core", "advisory", "issuing", "benchmark"},
    "whatif": {"core", "whatif"},
}
# The built-in what-if models wrap domain calculators by design.
EXCEPTIONS = {("whatif", "models.py"): {"issuing", "customer"}}


def cardwise_imports(path: Path) -> set[str]:
    layers = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        names: list[str] = []
        if isinstance(node, ast.ImportFrom) and node.module:
            names = [node.module]
        elif isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        for name in names:
            parts = name.split(".")
            if parts[0] == "cardwise" and len(parts) > 1:
                layers.add(parts[1])
    return layers


@pytest.mark.parametrize("layer", sorted(ALLOWED))
def test_layer_imports(layer: str) -> None:
    for path in sorted((PACKAGE / layer).glob("*.py")):
        allowed = ALLOWED[layer] | EXCEPTIONS.get((layer, path.name), set())
        illegal = cardwise_imports(path) - allowed
        assert not illegal, f"{layer}/{path.name} imports {sorted(illegal)}"


def test_every_package_is_covered() -> None:
    packages = {p.name for p in PACKAGE.iterdir() if (p / "__init__.py").exists()}
    assert packages - {"web"} == set(ALLOWED)
