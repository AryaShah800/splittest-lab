# SplitTest Lab: A/B test analysis of a mobile-game gate change

**Business question:** does moving the first progression gate in Cookie Cats from level 30 to level 40 change 7-day player retention?

**Answer:** yes, for the worse. 7-day retention fell from 19.02% to 18.20% (-0.82 pp, 95% CI -1.33 to -0.31, p = 0.0016), so the recommendation is to keep the gate at level 30. Caveats are listed below and in [`memo.md`](memo.md).

## Data
Cookie Cats mobile-game A/B test from Kaggle ("Mobile Games A/B Testing - Cookie Cats"): 90,189 players, one row each, with `userid`, `version` (`gate_30` / `gate_40`), `sum_gamerounds` (first 14 days), `retention_1` and `retention_7`. The file is not committed; download it and unzip it to `data/raw/cookie_cats_unzipped/cookie_cats.csv`.

## Approach
1. Write the experiment brief first, including the decision rule ([`brief.md`](brief.md)).
2. Check the design: sample ratio mismatch, duplicates, missing values, outliers.
3. Report the minimum detectable effect before the observed effect.
4. Test the primary metric (two-proportion z-test, bootstrap 95% CI) and the guardrail (Mann-Whitney U).
5. Run exploratory segments with a multiple-testing correction, plus a placebo check.
6. Write a ship / do-not-ship memo using the pre-written rule.

## Key findings
Every number is produced by `notebooks/01_ab_analysis.py` (see `results/ab_summary.json` and `results/segments.csv`).

- **Design checks:** no duplicates and no missing values. Group sizes are 44,700 (`gate_30`) and 45,489 (`gate_40`). The sample ratio check gives p = 0.0086: it passes the pre-set stop threshold (p < 0.001) but is a mild warning sign.
- **Power:** the test could detect a true difference of about 0.73 pp in 7-day retention (80% power, alpha 0.05).
- **Primary (7-day retention):** 19.02% vs 18.20%, difference -0.82 pp, z = -3.16, p = 0.0016. 95% CI -1.33 to -0.31 pp (analytic) and -1.33 to -0.32 pp (bootstrap).
- **Secondary (1-day retention):** 44.82% vs 44.23%, difference -0.59 pp, p = 0.074. Not significant.
- **Guardrail (game rounds):** medians 17 vs 16, Mann-Whitney p = 0.0502 (p = 0.0446 after trimming the top 0.1%). Borderline.
- **Decision by the pre-written rule:** keep `gate_30`.
- **Exploratory segments:** heavy players (more than 16 rounds) lose 1.09 pp (p = 0.0151, below the adjusted threshold of 0.0167); light players show no difference (-0.01 pp, p = 0.96). Rounds are measured after assignment, so this is descriptive only.
- **Placebo check:** players with fewer than 30 rounds should be unaffected by either gate, but show -0.33 pp (p = 0.049). Weak evidence that something besides the gate contributes, and consistent with the sample-ratio warning.

## Dashboard
A Tableau Public dashboard is not built yet.

## Reproduce
```bash
pip install -r requirements.txt
pytest -q                              # 21 unit tests on the statistics module
python notebooks/01_ab_analysis.py     # runs the analysis and writes results/
```

## Repo structure
```
splittest-lab/
├── brief.md                      # experiment design, written before looking at results
├── memo.md                       # one-page ship / do-not-ship decision memo
├── notebooks/01_ab_analysis.py   # the analysis, in the order the brief sets
├── src/splittest/stats.py        # tested statistics: SRM, z-test, bootstrap CI, MDE, Mann-Whitney, Bonferroni
├── tests/test_stats.py           # 21 unit tests (hand-derived values and statsmodels cross-checks)
├── results/                      # ab_summary.json, segments.csv, ab_summary.png
├── data/raw/                     # dataset goes here (git-ignored)
└── .github/workflows/tests.yml   # CI: pytest on every push
```
