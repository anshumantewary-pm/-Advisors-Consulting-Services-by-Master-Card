"""The committed samples in docs/samples must match what the code produces today."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_samples_are_up_to_date() -> None:
    script = ROOT / "scripts" / "render_samples.py"
    spec = importlib.util.spec_from_file_location("render_samples", script)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name, text in module.samples().items():
        committed = (ROOT / "docs" / "samples" / name).read_text(encoding="utf-8")
        assert committed == text, f"docs/samples/{name} is stale: run scripts/render_samples.py"
