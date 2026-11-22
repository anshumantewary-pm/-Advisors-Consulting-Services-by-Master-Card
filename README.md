# Cardwise

[![CI](https://github.com/anshumantewary-pm/-Advisors-Consulting-Services-by-Master-Card/actions/workflows/ci.yml/badge.svg)](https://github.com/anshumantewary-pm/-Advisors-Consulting-Services-by-Master-Card/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%20to%203.13-blue)
![Dependencies](https://img.shields.io/badge/runtime%20deps-0-brightgreen)

**Payments and banking advisory analytics.** Cardwise packages the analyses a payments consulting team runs for card issuers, acquirers and merchants: portfolio diagnostics with sized opportunities, card P&L, rewards and activation economics, merchant pricing, fraud strategy, delinquency and loss analytics, customer segmentation and experiments, market sizing, peer benchmarking, and wholesale credit decisioning. It is a Python library, a command-line tool and a browser app, with no runtime dependencies.

> Cardwise is an independent open-source project. It is not affiliated with, endorsed by or derived from Mastercard, its advisory business or any other card network. Benchmarks and defaults are indicative rules of thumb, not market data; validate with client data before using any figure.

```console
$ cardwise review examples/portfolio-review.json
Harbour Bank Cards · Mass-market credit card
Health score    14/100
Pre-tax profit  $12.2M (ROA 0.49%)
Opportunity     $40.7M a year

  Active rate                        52.0%   GAP
  Revolve rate                       42.0%   GAP
  Net credit loss rate                5.8%   GAP
  Rewards cost / spend                0.9%   GAP
  Pre-tax ROA                         0.5%   GAP
  Authorisation approval rate        83.0%   GAP
  Fraud losses (bp of spend)        6.7 bp   within

Top opportunities
     $20.0M  Reduce net credit loss rate
     $11.4M  Raise revolve rate
      $7.8M  Reduce rewards cost / spend
    $789.4K  Raise authorisation approval rate
    $701.5K  Raise active rate
```

## How to launch

| What | How | Link |
|---|---|---|
| **Web workbench, hosted** | Live once this repository's `main` branch deploys to GitHub Pages | `https://anshumantewary-pm.github.io/-Advisors-Consulting-Services-by-Master-Card/` |
| **Web workbench, local** | `scripts/build_site.sh --serve` | http://localhost:8000 |
| **Command line** | `cardwise --help` | terminal |
| **Python** | `import cardwise` | notebook or service |

First-time setup:

```bash
git clone https://github.com/anshumantewary-pm/-Advisors-Consulting-Services-by-Master-Card.git
cd -Advisors-Consulting-Services-by-Master-Card
pip install -e ".[dev]"
```

To switch on the hosted workbench, enable GitHub Pages once: **Settings → Pages → Source: GitHub Actions**. Every push to `main` then runs [`pages.yml`](.github/workflows/pages.yml), which tests, builds the wheel and publishes the site; the run summary shows the URL. The page loads Pyodide from the jsDelivr CDN, so it needs internet access; your data never leaves the browser.

## Quick start

```bash
cardwise review examples/portfolio-review.json --report review.md   # diagnosis + client report
cardwise credit examples/credit/northwind-industrial.json --memo memo.md
cardwise sensitivity card                                            # what drives card profit?
cardwise --help                                                      # every command
```

Every command takes `--json` for machine-readable output.

## What's inside

| Area | Commands | Library |
|---|---|---|
| **Advisory** | `review` (diagnosis, sized opportunities, target state, report), `compare`, `benchmark`, `types` | `advisory.diagnose`, `advisory.target_state`, `advisory.render_report`, `benchmark.scorecard` |
| **Issuing** | `pnl`, `bridge`, `rewards`, `activation`, `line-increase` | `issuing.card_pnl`, `pnl_bridge`, `portfolio_kpis`, `rewards_programme`, `activation_campaign`, `line_increase` |
| **Acquiring** | `pricing`, `merchant`, `chargebacks`, `merchants`, `enhanced-data` | `acquiring.compare_pricing`, `mdr_split`, `merchant_kpis`, `chargeback_cost`, `merchant_portfolio`, `enhanced_data_savings` |
| **Risk** | `fraud`, `threshold`, `rollrate`, `vintage`, `provision`, `collections` | `risk.rule_economics`, `best_threshold`, `rollrate.analyse`, `vintage_curves`, `provision`, `collections_strategy` |
| **Customer** | `rfm`, `cohort`, `clv`, `experiment`, `sample-size`, `retention` | `customer.rfm`, `cohort_retention`, `lifetime_value`, `two_proportion_test`, `retention_plan` |
| **Market** | `market`, `wallet` | `market.card_market`, `share_of_wallet` |
| **Credit** | `credit`, `collect`, `industries` | `credit.decide`, `render_memo`, `monitor` (CreditDecision) |
| **What-if** | `models`, `sensitivity`, `goalseek`, `simulate` | `whatif.tornado`, `goal_seek`, `simulate` on any model |

Example inputs for every file-based command are in [`examples/`](examples/); `cardwise examples` prints the command for each one.

## Library use

```python
from cardwise.advisory.diagnose import diagnose
from cardwise.advisory.io import review_from_dict
from cardwise.advisory.report import render_report
from cardwise.advisory.target import target_state

d = diagnose(review_from_dict(payload))          # KPIs, P&L, checks, sized opportunities
plan = target_state(d, {"net_credit_loss_rate": 0.5, "rewards_rate": 1.0})
markdown = render_report(d, plan)

from cardwise.issuing.pnl import CardEconomics, card_pnl
from cardwise.whatif.sensitivity import tornado

pnl = card_pnl(CardEconomics(active_accounts=6e5, purchase_volume=6e9,
                             receivables=2.4e9, revolving_balances=1.2e9))
```

Every result is a frozen dataclass with `to_dict()`, which is also the `--json` output.

## Project layout

```
src/cardwise/
├── core/        errors, validation, formatting, Result, JSON parsing
├── issuing/     portfolio KPIs, card P&L and bridge, rewards, activation, line increase
├── acquiring/   merchant pricing, merchant KPIs, chargebacks, merchant portfolio, L2/L3 data
├── risk/        fraud strategy, roll rates, vintages, provisions, early collections
├── customer/    RFM, cohorts, CLV, experiments, retention offers
├── market/      market sizing, share of wallet
├── benchmark/   peer percentiles, indicative KPI ranges by portfolio type
├── credit/      CreditDecision: decision, memo, monitoring and collections
├── advisory/    diagnosis, target state, report
├── whatif/      sensitivity, goal seek, scenarios, Monte Carlo, built-in models
└── cli.py       one command per analysis
web/index.html   browser workbench (Pyodide)
examples/        input files for every file-based command
docs/            architecture, services catalogue, methodology
```

Domain packages import only `core`; a test enforces the layering ([docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)).

## Development

```bash
pip install -e ".[dev]"
ruff check src tests && ruff format --check src tests
mypy
pytest --cov
```

CI runs lint, `mypy --strict`, tests on Linux, macOS and Windows with Python 3.10 to 3.13 (95% coverage floor), then builds and smoke-tests the wheel. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT. See [LICENSE](LICENSE).
