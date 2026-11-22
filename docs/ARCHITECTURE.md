# Architecture

Cardwise is a layered Python library with a thin CLI and a browser front end on top. Each layer imports only from the layers below it, and `tests/test_architecture.py` fails the build if that changes.

```
            ┌───────────────────────────────────────────────────────────┐
  Browser   │ web/index.html  tools declared as JSON; Pyodide installs   │
            │ the wheel and calls cli.build_parser() + the handler       │
            └──────────────────────────────┬────────────────────────────┘
                                           │
            ┌──────────────────────────────▼────────────────────────────┐
  Interface │ cli.py   @command registry, text or --json output          │
            └───────┬───────────────────────┬───────────────────┬───────┘
                    │                       │                   │
            ┌───────▼────────┐   ┌──────────▼─────────┐  ┌──────▼───────┐
  Use cases │ advisory/      │   │ whatif/            │  │ credit/      │
            │ diagnose,      │   │ sensitivity, goal  │  │ decision,    │
            │ target, report │   │ seek, scenarios,   │  │ memo,        │
            │                │   │ Monte Carlo,       │  │ collections  │
            │                │   │ models (wraps      │  │              │
            │                │   │ calculators)       │  │              │
            └───────┬────────┘   └──────────┬─────────┘  └──────┬───────┘
                    │                       │                   │
   ┌────────────────▼───────────────────────▼───┐               │
   │ Domain calculators (each imports only core) │               │
   │ issuing · acquiring · risk · customer ·     │               │
   │ market · benchmark                          │               │
   └────────────────────────┬────────────────────┘               │
                            │                                    │
            ┌───────────────▼────────────────────────────────────▼──┐
  Core      │ core/  errors · validate · formatting · Result · parse │
            └────────────────────────────────────────────────────────┘
```

## Layers

| Layer | Packages | Job | May import |
|---|---|---|---|
| Core | `core` | Errors, input validation, display formatting, the frozen `Result` base, typed JSON parsing | stdlib |
| Domain | `issuing`, `acquiring`, `risk`, `customer`, `market`, `benchmark` | Pure calculators returning frozen result dataclasses | core |
| Credit | `credit` | CreditDecision: wholesale lending decision, memo, monitoring and collections | core |
| Advisory | `advisory` | Portfolio diagnosis, target state, client report | core, issuing, benchmark |
| What-if | `whatif` | Model-agnostic sensitivity, goal seek, scenarios, Monte Carlo; `models.py` wraps calculators | core (+ issuing, customer in `models.py`) |
| Interface | `cli.py` | Parse arguments, read files, call the library, print text or JSON | everything |
| Web | `web/index.html` | Run CLI handlers in the browser | the built wheel |

## Design rules

1. **Pure functions.** Calculators take numbers and return values. No printing, files or globals; the CLI does all I/O.
2. **Validate at the edge.** Every public function checks its inputs and raises `ValidationError` naming the field (`economics.apr must be between 0 and 1`).
3. **Frozen, serialisable results.** Results subclass `core.Result`; `to_dict()` is the JSON contract for the CLI, the browser and any service.
4. **Show the work.** Multi-step figures carry `Step` lists (P&L lines, market sizing) and decompositions add up exactly (P&L bridge, MDR split, target-state bridge). Tests assert it.
5. **Indicative defaults, explicit inputs.** Benchmarks, chargeback bands, haircuts and policy thresholds are data a user can override, never logic buried in code.
6. **Reproducible randomness.** Monte Carlo uses a seeded `random.Random`.

## Data flow: `cardwise review examples/portfolio-review.json`

```
cli.main
  └─ read_json → advisory.io.review_from_dict        typed parse, field-level errors
       └─ advisory.diagnose(review)
            ├─ issuing.portfolio_kpis                active rate, revolve rate, ticket
            ├─ issuing.card_pnl                      revenue, costs, profit, ROA
            ├─ benchmark.ranges.get_portfolio_type   indicative KPI ranges
            └─ for each weak KPI: size the gap in money, attach levers, rank by value
       └─ advisory.target_state(diagnosis, 0.5)      change inputs together, recompute P&L,
                                                     bridge today → target (adds up exactly)
       └─ advisory.render_report                     Markdown client report
```

## Adding an analysis

1. Add a module to the right domain package with pure functions and frozen results; import only `core`.
2. Add `tests/test_<name>.py`: happy path, edge cases, validation errors.
3. Add a `@command` in `cli.py` and a CLI test.
4. Add the tool to the JSON list in `web/index.html`; `tests/test_web.py` runs it with its defaults automatically.
5. Document the formula in [METHODOLOGY.md](METHODOLOGY.md).

## CI/CD

```
push / PR ─► lint (ruff) ──────────┐
          ─► mypy --strict ────────┼─► build wheel ─► smoke-test in a clean venv
          ─► pytest 3 OS × 4 Py ───┘                  ─► example review in the job summary
push main ─► pages.yml: test ─► scripts/build_site.sh ─► GitHub Pages
tag v*    ─► release.yml: build ─► GitHub Release with the wheel and sdist
weekly    ─► Dependabot (Actions, pip)
```
