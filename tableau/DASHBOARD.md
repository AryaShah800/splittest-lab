# Tableau Public dashboard spec: Cookie Cats gate test

**Goal:** a one-page dashboard that a reader can understand in 30 seconds: the result, how sure we are, and where it concentrates.
**Data:** the three small files in this folder (aggregates only, no player rows). Regenerate them with `python notebooks/02_tableau_exports.py`.

| File | Grain | Use |
|---|---|---|
| `retention_by_version.csv` | version x metric (4 rows) | headline dot plot |
| `retention_by_rounds_bucket.csv` | version x rounds bucket x metric | engagement views |
| `headline_kpis.csv` | name / value | titles and annotations |

Fields in the two retention files: `version` (gate_30 / gate_40), `metric` (retention_1 / retention_7), `players`, `retained`, `rate`, `ci_low`, `ci_high` (Wilson 95%), plus `rounds_bucket` and `bucket_order` in the bucket file.

## Build steps (Tableau Public Desktop, free; or public.tableau.com web authoring)
1. **Connect** to the two retention files as *Text file* data sources. Add `headline_kpis.csv` as a third source.
2. **Sheet 1 "7-day retention with 95% CI"**
   - Filter `metric` = `retention_7`.
   - Rows: `version`. Columns: `SUM(rate)` as a **Circle** mark, colour by `version`.
   - Add an interval: calculated field `ci_width = [ci_high] - [ci_low]`. Drag `SUM(ci_low)` to Columns to make a second axis, mark type **Gantt Bar**, Size = `SUM(ci_width)`; make it a dual axis and synchronise. Format the axis as percentage.
3. **Sheet 2 "Retention by game rounds"**
   - Filter `metric` = `retention_7`. Columns: `rounds_bucket` (sort by `bucket_order`). Rows: `SUM(rate)`. Colour: `version`. Line with circles. Add `SUM(ci_low)` and `SUM(ci_high)` as light bands if wanted.
4. **Sheet 3 "Difference by game rounds (gate_40 minus gate_30)"**
   - Calculated field `signed_rate = IF [version] = 'gate_40' THEN [rate] ELSE -[rate] END`.
   - Filter `metric` = `retention_7`. Columns: `rounds_bucket` (sorted by `bucket_order`). Rows: `SUM(signed_rate)` formatted as percentage points. Bars; colour negative differences red, positive blue.
5. **Sheet 4 "Headline"**: text sheet using the values in `headline_kpis.csv` (see the exact wording below).
6. **Dashboard** (Desktop, about 1200 x 800): title, Sheet 4 across the top, Sheet 1 left, Sheets 2 and 3 stacked right, caveat text box along the bottom.

## Exact wording to use (so the dashboard matches the repo)
- **Title:** "Moving the gate to level 40 lowered 7-day retention"
- **Headline text:** "7-day retention: 19.02% (gate_30) vs 18.20% (gate_40). Difference -0.82 pp, 95% CI -1.33 to -0.31, p = 0.0016. Recommendation: keep gate_30."
- **Sheet 3 caption:** "Descriptive only: game rounds are measured after assignment, so this shows where the gap is, not why."
- **Caveat box:**
  - "Sample ratio check p = 0.0086: the 50/50 split was slightly off, a mild warning about assignment."
  - "Players with under 30 rounds (who should not see either gate) show a -0.33 pp gap (p = 0.049), so something besides the gate may contribute."
  - "Data: 90,189 Cookie Cats players (Kaggle). 1-day and 7-day retention only; no revenue."
- **Source line:** link to the GitHub repo (add after publishing).

## What the data shows in sheets 2 and 3 (check your build against this)
- The 7-day retention gap is largest at 50 to 99 rounds (gate_30 37.5% vs gate_40 32.9%), also visible at 20 to 29 (11.4% vs 10.0%) and 40 to 49 (22.2% vs 19.7%).
- At 100+ rounds the two versions are the same (about 61% and 85%), and light players (under 10 rounds) differ by well under 1 pp.

## Publish (this needs your Tableau Public account)
1. Sign in to Tableau Public (free) and choose **File > Save to Tableau Public As...**, with a descriptive name such as "Cookie Cats gate test".
2. In the published page, set **Show sheet tabs** off, then copy the public URL.
3. Send me the URL. I will add it to the repo README and the resume, and check that the page matches the numbers above before using it.
