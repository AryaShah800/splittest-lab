# %% [markdown]
# # Cookie Cats A/B test: does moving the first gate from level 30 to level 40 change 7-day retention?
# Follows `brief.md` in the order it was written: design checks, power, primary test, guardrail, exploratory segments.
# Every number printed here is the only source for numbers in the README, memo and resume.

# %%
import sys, json, pathlib, numpy as np, pandas as pd, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from splittest import stats as s

DATA = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "raw" / "cookie_cats_unzipped" / "cookie_cats.csv"
RESULTS = ROOT / "results"; RESULTS.mkdir(exist_ok=True)
ALPHA = 0.05
out = {}

df = pd.read_csv(DATA)
print(f"[load] {DATA.name}: {len(df):,} rows, columns {list(df.columns)}")

# %% [markdown]
# ## 1. Design checks (before looking at any effect)

# %%
n_a = int((df.version == "gate_30").sum()); n_b = int((df.version == "gate_40").sum())
srm = s.srm_check(n_a, n_b)
dup_ids = int(df.userid.duplicated().sum())
missing = int(df.isna().sum().sum())
print(f"Group sizes: gate_30 (control) {n_a:,} | gate_40 (treatment) {n_b:,} | share control {srm['share_a']:.4f}")
print(f"SRM chi-square {srm['chi2']:.3f}, p = {srm['p_value']:.4f}  ->  {'MISMATCH: stop and investigate' if srm['p_value'] < 0.001 else 'no mismatch at the 0.001 threshold'}")
print(f"Duplicate userids: {dup_ids} | missing values: {missing} | unexpected version values: {sorted(set(df.version) - {'gate_30', 'gate_40'})}")

r = df.sum_gamerounds
q = r.quantile([.5, .9, .99, .999]).to_dict()
print(f"Game rounds: median {q[.5]:.0f}, p90 {q[.9]:.0f}, p99 {q[.99]:.0f}, p99.9 {q[.999]:.0f}, max {r.max():,} | players with 0 rounds: {(r == 0).sum():,} ({(r == 0).mean():.1%})")
top = df.nlargest(3, "sum_gamerounds")[["userid", "version", "sum_gamerounds"]]
print("Three largest values:\n" + top.to_string(index=False))
out["design"] = dict(n_control=n_a, n_treatment=n_b, srm_chi2=srm["chi2"], srm_p=srm["p_value"], duplicates=dup_ids, missing=missing,
                     zero_round_players=int((r == 0).sum()), median_rounds=float(q[.5]), p99_rounds=float(q[.99]), max_rounds=int(r.max()))

# %% [markdown]
# ## 2. Power: the smallest difference this test could detect (80% power, alpha 0.05)

# %%
ctrl, trt = df[df.version == "gate_30"], df[df.version == "gate_40"]
base7, base1 = float(ctrl.retention_7.mean()), float(ctrl.retention_1.mean())
mde7 = s.mde_two_proportions(n_a, n_b, base7); mde1 = s.mde_two_proportions(n_a, n_b, base1)
print(f"Control baseline: 7-day retention {base7:.2%}, 1-day retention {base1:.2%}")
print(f"Minimum detectable difference: 7-day {mde7*100:.2f} pp | 1-day {mde1*100:.2f} pp")
out["power"] = dict(baseline_7=base7, baseline_1=base1, mde_7_pp=mde7 * 100, mde_1_pp=mde1 * 100)

# %% [markdown]
# ## 3. Primary test: 7-day retention (gate_40 minus gate_30)

# %%
def test_rate(col):
    x_a, x_b = int(ctrl[col].sum()), int(trt[col].sum())
    z = s.two_proportion_ztest(x_a, n_a, x_b, n_b)
    b = s.bootstrap_proportion_diff_ci(x_a, n_a, x_b, n_b, n_boot=20000, seed=42)
    return z, b

z7, b7 = test_rate("retention_7")
print(f"7-day retention: gate_30 {z7['rate_a']:.2%} ({int(ctrl.retention_7.sum()):,}/{n_a:,}) vs gate_40 {z7['rate_b']:.2%} ({int(trt.retention_7.sum()):,}/{n_b:,})")
print(f"Difference {z7['diff']*100:+.2f} pp | z = {z7['z']:.3f}, p = {z7['p_value']:.4f}")
print(f"95% CI: analytic [{z7['ci_low']*100:+.2f}, {z7['ci_high']*100:+.2f}] pp | bootstrap [{b7['ci_low']*100:+.2f}, {b7['ci_high']*100:+.2f}] pp")
out["primary_retention_7"] = dict(rate_control=z7["rate_a"], rate_treatment=z7["rate_b"], diff_pp=z7["diff"] * 100, z=z7["z"], p=z7["p_value"],
    ci_analytic_pp=[z7["ci_low"] * 100, z7["ci_high"] * 100], ci_bootstrap_pp=[b7["ci_low"] * 100, b7["ci_high"] * 100])

z1, b1 = test_rate("retention_1")
print(f"\n1-day retention (secondary): gate_30 {z1['rate_a']:.2%} vs gate_40 {z1['rate_b']:.2%} | diff {z1['diff']*100:+.2f} pp | p = {z1['p_value']:.4f} | bootstrap 95% CI [{b1['ci_low']*100:+.2f}, {b1['ci_high']*100:+.2f}] pp")
out["secondary_retention_1"] = dict(rate_control=z1["rate_a"], rate_treatment=z1["rate_b"], diff_pp=z1["diff"] * 100, p=z1["p_value"],
    ci_bootstrap_pp=[b1["ci_low"] * 100, b1["ci_high"] * 100])

# %% [markdown]
# ## 4. Guardrail: game rounds (Mann-Whitney, skewed counts)

# %%
mw = s.mann_whitney(ctrl.sum_gamerounds, trt.sum_gamerounds)
cut = r.quantile(.999)
mw_trim = s.mann_whitney(ctrl.sum_gamerounds[ctrl.sum_gamerounds <= cut], trt.sum_gamerounds[trt.sum_gamerounds <= cut])
print(f"Median rounds: gate_30 {mw['median_a']:.0f} vs gate_40 {mw['median_b']:.0f} | Mann-Whitney p = {mw['p_value']:.4f} | P(control > treatment) = {mw['prob_a_larger']:.4f}")
print(f"Sensitivity, dropping rounds above the 99.9th percentile ({cut:.0f}): p = {mw_trim['p_value']:.4f}")
print(f"Mean rounds (outlier-sensitive, for reference): gate_30 {ctrl.sum_gamerounds.mean():.2f} vs gate_40 {trt.sum_gamerounds.mean():.2f}")
out["guardrail_rounds"] = dict(median_control=mw["median_a"], median_treatment=mw["median_b"], p=mw["p_value"], p_trimmed=mw_trim["p_value"],
    prob_control_larger=mw["prob_a_larger"], mean_control=float(ctrl.sum_gamerounds.mean()), mean_treatment=float(trt.sum_gamerounds.mean()))

# %% [markdown]
# ## 5. Decision rule from the brief
# Ship only if the primary difference is significant AND the whole 95% CI shows gate_40 is better AND the guardrail shows no significant drop.

# %%
sig = z7["p_value"] < ALPHA
ci_all_positive = b7["ci_low"] > 0
guardrail_drop = mw["p_value"] < ALPHA and mw["median_b"] < mw["median_a"]
if srm["p_value"] < 0.001:
    decision = "NO DECISION: sample ratio mismatch, investigate assignment"
elif sig and ci_all_positive and not guardrail_drop:
    decision = "SHIP gate_40"
elif sig and z7["diff"] < 0:
    decision = "KEEP gate_30 (gate_40 is significantly worse on 7-day retention)"
else:
    decision = "KEEP gate_30 (no significant improvement)"
print("Decision by the pre-written rule:", decision)
out["decision"] = decision

# %% [markdown]
# ## 6. Exploratory segments (cannot change the decision)
# Caveat: game rounds are measured after assignment, so the gate change can itself influence which segment a player lands in.
# Segment results are therefore descriptive. The placebo row checks players who never reached either gate.

# %%
med = float(r.median())
segments = {"light players (rounds <= median)": df.sum_gamerounds <= med, "heavy players (rounds > median)": df.sum_gamerounds > med,
            "played under 30 rounds (placebo: never reached a gate)": df.sum_gamerounds < 30,
            "played 30+ rounds (reached the level-30 gate)": df.sum_gamerounds >= 30}
family = 3  # light, heavy, 30+ rounds are the tested family; the placebo is a validity check, not a finding
thr = s.bonferroni_threshold(ALPHA, family)
rows = []
for name, mask in segments.items():
    sub = df[mask]; sa, sb = sub[sub.version == "gate_30"], sub[sub.version == "gate_40"]
    t = s.two_proportion_ztest(int(sa.retention_7.sum()), len(sa), int(sb.retention_7.sum()), len(sb))
    rows.append(dict(segment=name, n_control=len(sa), n_treatment=len(sb), rate_control=t["rate_a"], rate_treatment=t["rate_b"],
                     diff_pp=t["diff"] * 100, ci_low_pp=t["ci_low"] * 100, ci_high_pp=t["ci_high"] * 100, p=t["p_value"],
                     significant_at_adjusted_threshold=bool(t["p_value"] < thr)))
seg = pd.DataFrame(rows); seg.to_csv(RESULTS / "segments.csv", index=False)
print(f"Median rounds used for the light/heavy split: {med:.0f} | Bonferroni threshold for {family} tests: {thr:.4f}")
print(seg.assign(rate_control=lambda d: (d.rate_control * 100).round(2), rate_treatment=lambda d: (d.rate_treatment * 100).round(2),
                 diff_pp=lambda d: d.diff_pp.round(2), ci_low_pp=lambda d: d.ci_low_pp.round(2), ci_high_pp=lambda d: d.ci_high_pp.round(2),
                 p=lambda d: d.p.round(4)).to_string(index=False))
out["segments_threshold"] = thr

# %% [markdown]
# ## 7. Chart

# %%
fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
# Left: point estimates with 95% intervals (a dot plot, so a non-zero axis does not exaggerate the gap)
for i, (label, rate, n, color) in enumerate([("gate_30 (control)", z7["rate_a"], n_a, "#4C78A8"), ("gate_40", z7["rate_b"], n_b, "#E4572E")]):
    half = 1.96 * np.sqrt(rate * (1 - rate) / n) * 100
    ax[0].errorbar(rate * 100, i, xerr=half, fmt="o", color=color, capsize=6, markersize=8)
    ax[0].text(rate * 100, i + 0.18, f"{rate * 100:.2f}%", ha="center", va="bottom", color=color)
ax[0].set_yticks([0, 1], ["gate_30 (control)", "gate_40"]); ax[0].set_ylim(-0.6, 1.6); ax[0].invert_yaxis()
ax[0].set(title=f"7-day retention with 95% CI\ndifference {z7['diff']*100:+.2f} pp, p = {z7['p_value']:.4f}", xlabel="% of players still playing after 7 days")
ax[0].grid(axis="x", alpha=.3)
# Right: rounds on log-spaced bins; players with zero rounds are counted separately because log(0) is undefined
played = df.sum_gamerounds[df.sum_gamerounds >= 1]
ax[1].hist(played, bins=np.logspace(0, np.log10(played.max()), 45), color="#4C78A8")
ax[1].set_xscale("log")
ax[1].set(title="Game rounds per player", xlabel=f"rounds in first 14 days, log scale ({(r == 0).sum():,} players with 0 rounds not shown)", ylabel="players")
plt.tight_layout(); fig.savefig(RESULTS / "ab_summary.png", dpi=150)

(RESULTS / "ab_summary.json").write_text(json.dumps(out, indent=2, default=float), encoding="utf-8")
print("\nSaved results/ab_summary.json, results/segments.csv, results/ab_summary.png")
