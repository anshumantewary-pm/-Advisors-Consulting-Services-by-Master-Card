# Contributing

Thanks for helping. Cardwise aims to be the toolkit a payments consulting team reaches for, so every analysis should be correct, traceable and easy to explain to a client.

## Set up

```bash
pip install -e ".[dev]"
pre-commit install   # optional: ruff and file checks on every commit
```

## Before you open a pull request

```bash
ruff check src tests && ruff format --check src tests
mypy
pytest --cov
```

CI runs the same checks on Linux, macOS and Windows with Python 3.10 to 3.13, and fails below 95% coverage.

## Adding an analysis

Follow [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#adding-an-analysis):

1. Pure functions in the right domain package; import only `cardwise.core`.
2. Validate every input with `core.validate` so errors name the field.
3. Return a frozen dataclass that subclasses `core.Result`.
4. Test the happy path, edge cases (zeros, empty inputs) and every validation error. Where figures decompose, assert that the parts add up.
5. Add a `@command` in `cli.py` and a CLI test, then add the tool to `web/index.html`.
6. Write the formula in [docs/METHODOLOGY.md](docs/METHODOLOGY.md).

## Benchmarks and defaults

Default ranges, thresholds and haircuts are indicative screening values. If you change one, say where the new figure comes from in the pull request, and keep it overridable.

## Independence

Cardwise is not affiliated with any card network or its advisory business. Do not add logos, trademarks or proprietary data from any company.
