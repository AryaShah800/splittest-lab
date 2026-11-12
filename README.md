# SplitTest Lab: A/B test analysis of a mobile-game gate change

**Business question:** does moving the first progression gate in Cookie Cats from level 30 to level 40 change 7-day player retention?

**Status:** work in progress. The experiment brief, the tested statistics code and CI are done; the analysis on the real data has **not been run yet**, so there are no results in this repo.

| Step | State |
|---|---|
| Experiment brief (hypotheses, metrics, decision rule, written before the data) | Done: [`brief.md`](brief.md) |
| Statistics functions: SRM check, z-test, bootstrap CI, minimum detectable effect, Mann-Whitney, Bonferroni | Done: [`src/splittest/stats.py`](src/splittest/stats.py) |
| Unit tests (21) and GitHub Actions CI | Done: [`tests/`](tests/) |
| Data checks, power analysis, tests, segments | Waiting for the dataset |
| Tableau Public dashboard | Not started |
| Decision memo | Not started |

## Data
[Mobile Games A/B Testing - Cookie Cats](https://www.kaggle.com/) on Kaggle: one row per player with `userid`, `version` (`gate_30` / `gate_40`), `sum_gamerounds`, `retention_1`, `retention_7`. The file is not committed; download it into `data/raw/cookie_cats.csv`.

## Approach
1. Write the experiment brief first (hypotheses, primary metric, guardrail, decision rule).
2. Check the design: sample ratio mismatch, duplicates, outliers.
3. Report the minimum detectable effect before the observed effect.
4. Test the primary metric (two-proportion z-test, bootstrap 95% CI) and the guardrail (Mann-Whitney).
5. Run exploratory segments with a multiple-testing correction.
6. Write a ship / do-not-ship memo using the pre-written decision rule.

## Reproduce
```bash
pip install -r requirements.txt
pytest -q
```

## Repo structure
```
splittest-lab/
├── brief.md                 # experiment design, written before looking at results
├── src/splittest/stats.py   # the tested statistics functions
├── tests/test_stats.py      # 21 unit tests (hand-derived values and statsmodels cross-checks)
├── data/raw/                # dataset goes here (git-ignored)
└── .github/workflows/       # CI: pytest on every push
```
