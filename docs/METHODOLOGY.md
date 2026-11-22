# Methodology

The formula behind every figure Cardwise produces. Rates are fractions per year unless stated; "bp" is basis points (1 bp = 0.01%).

## Issuing

**Portfolio KPIs** (`issuing.portfolio`)
- Active rate = active accounts / open accounts
- Spend per active = purchase volume / active accounts
- Revolve rate = revolving (interest-bearing) balances / receivables
- Average ticket = purchase volume / transactions

**Card P&L** (`issuing.pnl`)

| Line | Formula |
|---|---|
| Interchange | purchase volume × interchange rate |
| Interest | revolving balances × APR |
| Fees | fee income (input) |
| Funding cost | receivables × cost of funds |
| Rewards cost | purchase volume × rewards rate |
| Net credit losses | receivables × net credit loss rate |
| Network fees | purchase volume × network fee rate |
| Operating cost | active accounts × cost per account |
| **Pre-tax profit** | revenue − all costs; ROA = profit / receivables |

The **P&L bridge** attributes the profit change to each line (revenue lines +, cost lines −); the drivers sum exactly to the change.

**Rewards** (`issuing.rewards`)
- Effective rewards rate = points per unit × point value × (1 − breakage)
- Incremental margin = baseline spend × lift × (interchange − network fees)
- Programme cost = rewards rate × baseline × (1 + lift) + fixed cost
- Break-even lift = (rate × baseline + fixed) / (baseline × (margin − rate)); none if margin ≤ rate

**Activation** (`issuing.activation`)
- Incremental activations = targeted × (response − control)
- Cost = targeted × contact cost + targeted × response × incentive (incentives also go to those who would have activated anyway)
- Value per new active = Σₜ profit × retentionᵗ / (1 + d)ᵗ⁺¹ over the horizon

## Acquiring

- **MDR split**: merchant cost = volume × MDR = interchange + scheme fees + acquirer margin
- **Blended interchange** = Σ share × interchange rate (shares must sum to 1)
- **IC++ MDR** = blended interchange + scheme fee + markup; margin-neutral markup = blended MDR − interchange − scheme fee
- **Chargeback ratio** = chargebacks / approved transactions; bands (early warning, standard, excessive) are configurable, indicative defaults 0.65%, 0.9%, 1.5%
- **Chargeback net loss** = disputed value × goods-lost share + fees + handling + contest costs − value recovered; contest if win rate × value × lost share > contest cost
- **Merchant contribution** = volume × (MDR − interchange − scheme fee) − cost to serve; repriced MDR = interchange + scheme fee + cost to serve / volume + target margin

## Risk

- **Fraud rate** = fraud losses / sales × 10,000 bp
- **Rule economics**: precision = TP / (TP + FP); recall = TP / (TP + FN); insult cost = FP × (good value × margin + churn cost); total cost = FN × fraud value + insult cost
- **Best threshold** scans every distinct score (decline if score ≥ threshold) and "decline nothing", and keeps the lowest total cost
- **Roll rates**: row-normalised transition matrix between buckets, charge-off absorbing; forward roll rate = P(bucket → next bucket); flow-through = product of forward roll rates; projection = balances × matrixᵐ
- **Vintages**: cumulative loss rate = Σ monthly losses / originated, by months on book; lifetime estimate = loss at month m / seasoning share at m
- **Provisions**: stage 1 (current, 1-29 dpd) ECL = balance × PD₁₂ × LGD; stage 2 (30-89) uses lifetime PD = 1 − (1 − PD₁₂)^years; stage 3 (90+) PD = 1. The lifetime view applies lifetime PD to every bucket.

## Customer

- **RFM**: quintile scores 1-5 by rank (ties share a score); recency scored inversely; segments from the R × F grid
- **Cohorts**: retention at offset k = members active in cohort + k / cohort size; average weighted by cohort size
- **CLV** = margin / (1 + d − r) for constant retention r (margin received at year end); lifetime = 1 / (1 − r); max CAC = CLV / target LTV:CAC
- **Experiments**: two-proportion z-test with pooled standard error; CI on the lift uses the unpooled standard error; sample size per arm from the normal approximation with the stated confidence and power
- **Retention offers**: value per customer = churn probability × save rate × CLV − offer cost; target if positive; break-even save rate = cost / (churn probability × CLV)

## Market

- Card spend = population × spend per capita × card share; future spend grows at the spend growth rate; cash displaced = future spend × (target share − today's share); revenue pool = future card spend × revenue yield
- Share of wallet = our card spend / customers' total card spend; opportunity = target share × total − our spend

## Benchmarking and diagnosis

- **Percentiles** use linear interpolation (Excel PERCENTILE.INC). Percentile rank = share of peers beaten, ties counted half; quartile 1 is best whichever direction is good.
- **Diagnosis** compares each KPI with the portfolio type's indicative range. A weak KPI is sized as the annual pre-tax profit of reaching the edge of the range:

| KPI | Value of closing the gap |
|---|---|
| Active rate | extra actives × profit per active |
| Revolve rate | gap × receivables × (APR − loss rate) |
| Net credit loss rate | gap × receivables |
| Rewards rate | gap × purchase volume |
| Approval rate | recovered volume × (interchange − network fees − rewards) |
| Fraud | gap (bp) × purchase volume |

ROA is checked but not sized: it is the outcome of the levers above.

- **Target state** closes a chosen share of each gap together, in a fixed order (activation and approvals scale volumes and balances first), recomputes the full P&L and bridges today's profit to the target. Because inputs change together, overlaps are not double-counted.

## Credit (CreditDecision)

See `cardwise.credit` docstrings: an 11-factor scorecard maps to a 10-grade master scale with PDs; LGD blends a 20% secured and 40% (senior) or 75% (subordinated) unsecured loss using collateral haircuts; regulatory capital uses the Basel IRB corporate formula (5 bp PD floor, 1-5 year maturity); RAROC = (drawn × (margin − funding spread) + fees − cost to serve − EL) × (1 − tax) / capital.

## What-if

- **Tornado**: each input moved to its low and high value (default ±10%) with the others at base; bars sorted by swing
- **Goal seek**: bisection on the bracket given
- **Monte Carlo**: independent draws from each input distribution with a fixed seed; reports mean, percentiles, P(output < threshold) and a histogram
