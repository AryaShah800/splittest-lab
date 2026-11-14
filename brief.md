# Experiment brief: moving the first gate in Cookie Cats from level 30 to level 40

**Written before running the analysis** (the commit history shows this brief committed before any results). This is a retrospective analysis of a public dataset, so the design was not pre-registered and the assignment was not run by me. Everything below is the plan; the results go in `memo.md` after the analysis.
Dataset: Cookie Cats mobile-game A/B test (Kaggle), one row per player with `userid`, `version` (`gate_30` or `gate_40`), `sum_gamerounds`, `retention_1`, `retention_7`.

## Question
Does moving the first progression gate from level 30 (control) to level 40 (treatment) change how many players are still playing a week after install?

## Hypotheses
- **H0:** the 7-day retention rate is the same under `gate_30` and `gate_40`.
- **H1:** the 7-day retention rates differ (two-sided; I do not assume which direction, because a later gate could help by keeping the game fun for longer or hurt by delaying the "pause" that brings players back).

## Metrics
| Role | Metric | Definition |
|---|---|---|
| **Primary** | 7-day retention | share of players with `retention_7 = True` |
| Secondary | 1-day retention | share with `retention_1 = True` |
| Guardrail | Game rounds played in the first 14 days | `sum_gamerounds` (compared with Mann-Whitney U, since the distribution is heavily skewed) |

## Design checks to run before reading any effect
1. **Sample ratio mismatch (SRM):** chi-square test of the observed `gate_30` / `gate_40` split against 50/50. If p < 0.001, stop and investigate the assignment, do not interpret the result.
2. **Data quality:** duplicate `userid`s, missing values, extreme `sum_gamerounds` outliers (reported and handled openly, not silently dropped).
3. **Power:** report the minimum detectable absolute difference in 7-day retention for this sample size (80% power, alpha 0.05, two-sided) *before* showing the observed difference, so a null result can be read correctly.

## Analysis plan
- **Primary test:** two-proportion z-test on 7-day retention, with a 95% confidence interval on the absolute difference (`gate_40` minus `gate_30`) from a bootstrap, cross-checked against the analytic interval.
- **Guardrail test:** Mann-Whitney U on game rounds, with medians reported.
- **Segments (exploratory only):** light vs heavy players, split by median game rounds. Because this adds several extra comparisons, any segment p-value is reported with a Bonferroni-adjusted threshold and labelled exploratory. Segments cannot change the decision.
- **Significance level:** alpha = 0.05 for the primary metric only.

## Decision rule (fixed in advance)
| Outcome | Decision |
|---|---|
| Primary difference is significant at 0.05 **and** the whole 95% CI shows `gate_40` is better | Ship `gate_40`, provided the guardrail shows no significant drop in game rounds |
| Primary difference is significant at 0.05 and `gate_40` is worse | Keep `gate_30` |
| CI includes 0 (not significant) | Keep `gate_30`: there is no evidence the change helps, and shipping a change needs evidence. State the minimum detectable effect so the reader knows what this test could and could not detect. |
| SRM check fails | No decision; investigate the assignment first |

## Known limits (stated up front)
- Observational outcome windows are fixed by the dataset (1 and 7 days); long-term retention and revenue are not measured.
- The data has no timestamps or user attributes, so I cannot check for novelty effects, weekday effects or device mix.
- Retention flags are a single snapshot, so this tests whether players returned on the specific day, not their full activity pattern.
