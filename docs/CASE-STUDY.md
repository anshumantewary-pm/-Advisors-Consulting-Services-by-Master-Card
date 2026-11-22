# Case study: Harbour Bank Cards

A worked example of a first-pass card portfolio engagement using Cardwise. Harbour Bank is fictional; every figure below comes from the files in [`examples/`](../examples/) and can be reproduced with the commands shown.

## 1. The question

Harbour Bank's mass-market credit card portfolio (1 million accounts, $2.5B of receivables) earned far less this year than last. The head of cards asks: *what went wrong, what is it worth to fix, and where do we start?*

## 2. What changed? The P&L bridge

```bash
cardwise bridge examples/pnl-bridge.json
```

```
Pre-tax profit before        71.2M

  credit losses            -37.0M
  funding cost             -28.5M
  rewards cost              -4.4M
  network fees            -240.0K
  interchange             +900.0K
  operating cost            +2.7M
  fees                      +3.0M
  interest                  +4.5M

Pre-tax profit after         12.2M  (-59.0M)
```

Two lines explain almost all of the fall: credit losses rose from 4.5% to 5.8% of receivables, and funding cost rose with rates (3.5% to 4.5%). Higher APR and fees offset only a fraction.

## 3. How does the portfolio compare? The diagnosis

```bash
cardwise review examples/portfolio-review.json --report review.md
```

The full report is in [samples/portfolio-review-report.md](samples/portfolio-review-report.md). The health score is 14/100: 5 levers sit outside the typical range for a mass-market portfolio, together worth about $40.7M a year before tax. Credit losses lead (about $20.0M), then revolve rate (about $11.4M) and rewards cost (about $7.8M).

## 4. What drives profit most? Sensitivity

The built-in `card` model, set to Harbour Bank's figures, moves each input ±10% with the others held still:

```bash
cardwise sensitivity card --set receivables=2.5e9 --set revolving_balances=1.05e9 \
  --set net_credit_loss_rate=0.058 --set apr=0.21 ...   # all ten inputs in the case
```

```
Base pre-tax profit: 12.2M

receivables                   37.9M ..     -13.6M   swing 51.5M
revolving_balances            -9.9M ..      34.2M   swing 44.1M
apr                           -9.9M ..      34.2M   swing 44.1M
net_credit_loss_rate          26.7M ..      -2.3M   swing 29.0M
cost_of_funds                 23.4M ..     910.0K   swing 22.5M
interchange_rate               3.3M ..      21.0M   swing 17.7M
```

Receivables top the list because, with interest-bearing balances held fixed, every extra unit of receivables only adds funding and loss cost: the balance sheet is carrying too many balances that earn nothing. Revolving balances and APR (the same lever from two sides) come next, then the loss rate. All three point to the same conclusion as the diagnosis.

## 5. Is the fix worth it? A collections business case

Most of the loss gap builds up in early delinquency. A digital-first collections strategy that lifts the early cure rate from 70% to 76%:

```bash
cardwise collections --balances 1.2e8 --accounts 40000 --cure-before 0.70 --cure-after 0.76 \
  --loss-given-no-cure 0.55 --cost-per-account 12
```

```
Losses before       19.8M
Losses after        15.8M
Losses avoided      4.0M
Strategy cost       480.0K
Net benefit         3.5M (ROI 725.0%)
Break-even uplift   0.73% of cure rate
```

## 6. The target state

Closing half of every gap at once moves pre-tax profit from $12.2M to $34.1M. Because the inputs change together and the P&L is recomputed, overlapping levers are not double-counted:

```bash
cardwise review examples/portfolio-review.json --achievement 0.5 --report review.md
```

## 7. Recommendation

1. **Losses first:** tighten acquisition cut-offs on the worst vintages (`cardwise vintage`) and fund the early-collections strategy above.
2. **Put idle balances to work:** balance-transfer and instalment offers to engaged transactors, and line increases only where the break-even loss rate leaves room (`cardwise line-increase`).
3. **Rebase rewards** on low-margin categories, testing the new earn rate with `cardwise rewards`.
4. **Track it:** re-run `cardwise review` each quarter and `cardwise bridge` at year end.

All ranges are indicative. In a real engagement, replace them with the bank's own peer set (`cardwise benchmark`).
