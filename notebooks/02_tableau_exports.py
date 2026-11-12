# %% [markdown]
# # Aggregate files for the Tableau Public dashboard
# Small summary tables (not the raw player rows) so the dashboard needs no row-level data and every figure reconciles to the analysis.

# %%
import sys, json, pathlib, pandas as pd
from statsmodels.stats.proportion import proportion_confint

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "raw" / "cookie_cats_unzipped" / "cookie_cats.csv"
OUT = ROOT / "tableau"; OUT.mkdir(exist_ok=True)
df = pd.read_csv(DATA)
summary = json.loads((ROOT / "results" / "ab_summary.json").read_text())


def wilson(x, n):
    lo, hi = proportion_confint(x, n, alpha=0.05, method="wilson")
    return lo, hi


# %% [markdown]
# ## 1. Retention by version (one row per version and metric)

# %%
rows = []
for version, g in df.groupby("version"):
    for metric in ("retention_1", "retention_7"):
        x, n = int(g[metric].sum()), len(g)
        lo, hi = wilson(x, n)
        rows.append(dict(version=version, metric=metric, players=n, retained=x, rate=x / n, ci_low=lo, ci_high=hi))
retention = pd.DataFrame(rows); retention.to_csv(OUT / "retention_by_version.csv", index=False)

# %% [markdown]
# ## 2. Retention by engagement bucket (game rounds in the first 14 days)
# The buckets are plain ranges. Rounds are measured after assignment, so this view is descriptive.

# %%
edges = [-1, 0, 4, 9, 19, 29, 39, 49, 99, 199, float("inf")]
labels = ["0", "1-4", "5-9", "10-19", "20-29", "30-39", "40-49", "50-99", "100-199", "200+"]
df["rounds_bucket"] = pd.cut(df.sum_gamerounds, bins=edges, labels=labels)
rows = []
for (version, bucket), g in df.groupby(["version", "rounds_bucket"], observed=True):
    for metric in ("retention_1", "retention_7"):
        x, n = int(g[metric].sum()), len(g)
        lo, hi = wilson(x, n)
        rows.append(dict(version=version, rounds_bucket=bucket, bucket_order=labels.index(bucket), metric=metric, players=n, retained=x,
                         rate=x / n, ci_low=lo, ci_high=hi))
bucket = pd.DataFrame(rows).sort_values(["metric", "bucket_order", "version"]); bucket.to_csv(OUT / "retention_by_rounds_bucket.csv", index=False)

# %% [markdown]
# ## 3. Headline numbers for annotations (all copied from results/ab_summary.json)

# %%
p, d, pw, gr = summary["primary_retention_7"], summary["design"], summary["power"], summary["guardrail_rounds"]
kpi = pd.DataFrame([
    ("players_control", d["n_control"]), ("players_treatment", d["n_treatment"]),
    ("retention_7_control", p["rate_control"]), ("retention_7_treatment", p["rate_treatment"]),
    ("retention_7_diff_pp", p["diff_pp"]), ("retention_7_ci_low_pp", p["ci_analytic_pp"][0]), ("retention_7_ci_high_pp", p["ci_analytic_pp"][1]),
    ("retention_7_p_value", p["p"]), ("mde_7_pp", pw["mde_7_pp"]), ("srm_p_value", d["srm_p"]),
    ("median_rounds_control", gr["median_control"]), ("median_rounds_treatment", gr["median_treatment"]), ("guardrail_p_value", gr["p"]),
], columns=["name", "value"])
kpi.to_csv(OUT / "headline_kpis.csv", index=False)

# %% [markdown]
# ## 4. Reconciliation: every exported total must match the analysis

# %%
r7 = retention[retention.metric == "retention_7"].set_index("version")
assert r7.loc["gate_30", "players"] == d["n_control"] and r7.loc["gate_40", "players"] == d["n_treatment"]
assert abs(r7.loc["gate_30", "rate"] - p["rate_control"]) < 1e-12 and abs(r7.loc["gate_40", "rate"] - p["rate_treatment"]) < 1e-12
b7 = bucket[bucket.metric == "retention_7"]
assert b7.groupby("version").players.sum().to_dict() == {"gate_30": d["n_control"], "gate_40": d["n_treatment"]}
assert b7.groupby("version").retained.sum().to_dict() == r7.retained.to_dict()
print("Reconciliation passed. Files written to", OUT)
print(retention.round(4).to_string(index=False))
print(bucket[bucket.metric == "retention_7"].round(4).to_string(index=False))
