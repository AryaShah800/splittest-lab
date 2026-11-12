# Decision memo: should Cookie Cats move the first gate from level 30 to level 40?

**Recommendation: do not ship. Keep the gate at level 30.**

Players who saw the gate at level 40 were less likely to be playing 7 days later: 18.20% vs 19.02%, a drop of 0.82 percentage points (95% CI -1.33 to -0.31, p = 0.0016). That is roughly a 2% to 7% relative decline. This is the pre-agreed rule's outcome in `brief.md`: a significant result in the wrong direction means keep the control.

## What I tested
| | gate_30 (control) | gate_40 (treatment) | Difference | Result |
|---|---|---|---|---|
| Players | 44,700 | 45,489 | | |
| **7-day retention (primary)** | 19.02% | 18.20% | -0.82 pp (95% CI -1.33 to -0.31) | p = 0.0016 |
| 1-day retention (secondary) | 44.82% | 44.23% | -0.59 pp (bootstrap 95% CI -1.25 to +0.06) | p = 0.074, not significant |
| Game rounds, median (guardrail) | 17 | 16 | | Mann-Whitney p = 0.0502 |

The test could detect a true difference of about 0.73 percentage points in 7-day retention (80% power), so the observed 0.82 pp gap is just above what this sample is able to see.

## Checks and caveats, stated plainly
- **Sample ratio:** the split was 49.56% / 50.44% instead of 50 / 50 (chi-square p = 0.0086). It passes my pre-set stop threshold (p < 0.001) but is a mild warning sign about how players were assigned, so the result deserves slightly less trust than a perfectly balanced test.
- **Placebo check:** players who played fewer than 30 rounds should not be affected by either gate, yet their 7-day retention also differs slightly (-0.33 pp, p = 0.049, not clearly zero). That is weak evidence that something other than the gate contributes to the gap, and fits with the sample-ratio warning. It is borderline, not conclusive.
- **Guardrail:** game rounds are borderline lower under gate_40 (p = 0.0502; p = 0.0446 after trimming the most extreme 0.1% of players). It does not change the decision.
- **Segments are exploratory only.** Heavy players (more than the median 16 rounds) lose 1.09 pp (p = 0.0151, below the adjusted threshold of 0.0167); light players show no difference (-0.01 pp, p = 0.96). Because rounds are measured after assignment, the gate itself can influence which group a player lands in, so this suggests where the effect concentrates but does not prove it.
- **Outlier:** one player logged 49,854 rounds. Rank-based tests are not affected by it, and I kept every row.
- **Limits of the data:** only 1-day and 7-day retention are measured. There is no revenue, no long-term retention, no timestamps and no player attributes, so novelty effects and device mix cannot be checked.

## Why this decision
The change is not shown to help and is shown (with the caveats above) to be slightly harmful for the primary metric. Shipping a change needs evidence that it helps, and here the whole confidence interval is below zero.

## What I would do next
1. Ask how players were assigned, to understand the 49.56 / 50.44 split before trusting any further test.
2. If a later gate is still wanted (for example for monetisation reasons the data cannot show), run a larger, properly balanced test with revenue as an additional metric.

## Method, in four lines
- Design checks first (sample ratio, duplicates, missing values, outliers), then the minimum detectable effect before the observed effect.
- Two-proportion z-test with a bootstrap 95% CI cross-checked against the analytic CI; Mann-Whitney U for game rounds.
- Exploratory segments with a Bonferroni-adjusted threshold (0.0167 for 3 tests); the under-30-rounds group is a placebo check, not a finding.
- All statistics come from a unit-tested module (`src/splittest/stats.py`); every number above is in `results/ab_summary.json` and `results/segments.csv`.
