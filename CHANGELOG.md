# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [SemVer](https://semver.org/).

## [0.1.0] - 2026-11-22

First release.

### Added

- **Advisory**: portfolio diagnosis against indicative KPI ranges for mass, premium, commercial and debit portfolios, with every gap sized in money and the levers to close it; target-state P&L that closes a chosen share of each gap together and bridges from today; Markdown client report; side-by-side comparison of several portfolios; peer benchmarking (percentile rank, quartile, gaps).
- **Issuing**: portfolio KPIs; card P&L with traceable lines, ROA and profit per active; period-over-period P&L bridge; rewards programme ROI and closed-form break-even lift; activation campaign NPV and payback; credit line increase economics with a break-even loss rate.
- **Acquiring**: MDR split and blended vs interchange++ pricing; merchant KPIs (approval rate, decline mix, chargeback standing with configurable bands); chargeback cost and contest-or-accept; merchant portfolio profitability and repricing; Level 2/3 enhanced-data savings.
- **Risk**: fraud rule economics and cost-optimal score threshold; delinquency roll rates, flow-through and projections; loss vintage curves; IFRS 9 stage provisions and a CECL-style lifetime view; early-stage collections economics.
- **Customer**: RFM segmentation; cohort retention; lifetime value; two-proportion experiment reads and sample size; retention offer targeting.
- **Market**: card market sizing with cash displacement and revenue pool; share of wallet.
- **Credit**: CreditDecision, ported from The Consultant's Math: wholesale lending decision, IRB capital and RAROC, credit memo, monitoring and collections with US, IFRS 9 and RBI staging.
- **What-if**: sensitivity (tornado), goal seek, scenarios and seeded Monte Carlo on any model, with built-in card, rewards, CLV and merchant models.
- **CLI**: 36 commands, all with `--json`; `cardwise examples` lists a runnable command for every example file.
- **Web**: browser workbench (Pyodide) running every tool, with examples, rendered reports and memos, and JSON, Markdown and PDF export; `scripts/build_site.sh --serve` for a local preview; GitHub Pages deployment.
- **Quality**: 359 tests at 99% coverage, `mypy --strict`, ruff, an import-layering test, a test that runs every web tool through the CLI, and a test that keeps `docs/samples` in sync with the code. CI on Linux, macOS and Windows, Python 3.10 to 3.13; tag-triggered releases.
- **Docs**: README with a launch guide, architecture, services catalogue, methodology, worked case study, sample report and memo, contributing guide and security policy.
