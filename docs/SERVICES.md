# Services catalogue

The advisory engagements a payments consulting team typically runs, the client question behind each one, and the Cardwise tools that answer it. Use it to scope a proposal: each row is a deliverable you can produce from client data with the commands listed.

## Issuers (banks and card programmes)

| Engagement | Client question | Cardwise | Deliverable |
|---|---|---|---|
| Portfolio diagnostic | Where is our card business under-performing, and what is it worth to fix? | `review`, `compare`, `types`, `benchmark` | Health score, KPI gaps against typical ranges, opportunities sized in money with levers, target-state P&L, client report |
| Card P&L and profitability | Which lines drive profit, and what changed since last year? | `pnl`, `bridge`, `sensitivity card` | Line-by-line P&L, ROA, profit per active, year-on-year bridge that reconciles |
| Rewards optimisation | Does our rewards programme pay for itself? What spend lift do we need? | `rewards`, `sensitivity rewards` | Effective rewards rate, ROI, closed-form break-even lift, points liability |
| Activation and engagement | Should we pay to wake dormant cards? | `activation`, `experiment`, `sample-size` | Incremental actives, cost per incremental active, NPV, payback; test design and read |
| Customer value and retention | Which customers matter, who is at risk, and who is worth saving? | `rfm`, `cohort`, `clv`, `retention` | Segments and spend share, retention curves, lifetime value, targeted retention budget |
| Credit risk and losses | Are losses rising, and how much should we provide? | `rollrate`, `vintage`, `provision` | Roll rates and flow-through, vintage curves, IFRS 9 stage ECL and a lifetime view |
| Line management | Should we raise limits for good customers? | `line-increase` | Extra balances, interest and interchange against extra losses; break-even loss rate |
| Collections strategy | Is a new early-stage collections approach worth its cost? | `collections` | Losses avoided, net benefit, break-even cure-rate uplift |
| Fraud strategy | Are our rules catching fraud without insulting good customers? | `fraud`, `threshold` | Precision, recall, false-positive ratio, insult cost, cost-optimal score cut-off |
| Growth and market entry | How big is the card opportunity, and how much of our customers' wallet do we have? | `market`, `wallet` | Card market size, cash displacement, revenue pool, share and top-of-wallet, spend opportunity |

## Acquirers and merchants

| Engagement | Client question | Cardwise | Deliverable |
|---|---|---|---|
| Merchant pricing review | Blended or interchange++? Are we leaving margin behind? | `pricing` | MDR split (interchange, scheme, acquirer), merchant saving, margin-neutral markup |
| Merchant portfolio profitability | Which merchants lose money after cost to serve, and what should we charge them? | `merchants` | Contribution and basis points by merchant, loss makers, repricing MDR and uplift, concentration |
| Authorisation performance | How much revenue do declines cost? | `merchant`, library `approval_uplift_value` | Approval rate, decline mix, lost sales, value of an approval-rate uplift |
| Chargeback management | What do disputes cost, and should we fight them? | `chargebacks`, `merchant` | Net chargeback cost, contest-or-accept call, chargeback programme standing |
| B2B acceptance | What would passing Level 2/3 data save our commercial-card merchants? | `enhanced-data` | Effective interchange before and after, annual saving, payback |

## Corporate and commercial banking

| Engagement | Client question | Cardwise | Deliverable |
|---|---|---|---|
| Credit decisioning | Should we lend, on what terms, and who approves? | `credit`, `industries` | Decision, grade and PD, LGD, IRB capital, RAROC, policy exceptions, covenants, approver, 12-section credit memo |
| Portfolio monitoring and collections | Which facilities are deteriorating, how should we stage them and what do we do next? | `collect` | Covenant tests, early-warning signals, US / IFRS 9 / RBI staging, ECL, workout strategy with a dated plan |

## Cross-cutting

| Need | Cardwise |
|---|---|
| What drives the answer? | `sensitivity MODEL` (tornado) |
| What input gets us to the target? | `goalseek MODEL --vary NAME --target X --between LOW:HIGH` |
| How uncertain is it? | `simulate MODEL --dist NAME=SPEC` |
| Show it to the client | `review --report`, `credit --memo`, the web workbench's print-to-PDF |

All benchmarks and defaults are indicative. Replace them with the client's own data or peer set (`benchmark`) before presenting numbers as findings.
