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

## License

MIT. See [LICENSE](LICENSE).
