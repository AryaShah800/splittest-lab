"""Build docs/index.html (static report, findings first) from results/ab_summary.json, results/segments.csv and tableau/*.csv.
Usage: python scripts/build_report.py [--png] [--offline] [--out DIR]
The raw Kaggle file is not needed."""
import json
import sys
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
sys.path.insert(0, str(Path(__file__).parent))
from report_style import BLUE, ORANGE, MUTED, style, build_page, screenshot  # noqa: E402

R = Path(__file__).resolve().parents[1]
OUT = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else R / "docs"
s = json.load(open(R / "results" / "ab_summary.json"))
seg = pd.read_csv(R / "results" / "segments.csv")
byv = pd.read_csv(R / "tableau" / "retention_by_version.csv")
bkt = pd.read_csv(R / "tableau" / "retention_by_rounds_bucket.csv")

p7, p1, d, pw, gr = s["primary_retention_7"], s["secondary_retention_1"], s["design"], s["power"], s["guardrail_rounds"]
lo, hi = p7["ci_analytic_pp"]
rel = lambda x: x / (p7["rate_control"] * 100) * 100
heavy = seg[seg.segment.str.startswith("heavy")].iloc[0]
light = seg[seg.segment.str.startswith("light")].iloc[0]
placebo = seg[seg.segment.str.contains("placebo")].iloc[0]

insights = [
    dict(num=f"{p7['diff_pp']:.2f} pp",
         what=f"Moving the gate to level 40 cut 7-day retention from {p7['rate_control']*100:.2f}% to {p7['rate_treatment']*100:.2f}% (95% CI {lo:.2f} to {hi:.2f} pp, p = {p7['p']:.4f}).",
         action="Do not ship. Keep the gate at level 30, as the pre-written decision rule in brief.md requires.",
         impact=f"A {abs(rel(hi)):.1f}% to {abs(rel(lo)):.1f}% relative drop in the share of players still active after a week."),
    dict(num=f"{abs(p7['diff_pp'])*1000:,.0f} players",
         what="Per 100,000 new players, gate_40 would leave about this many fewer active on day 7 (simple arithmetic on the point estimate).",
         action="Use this as the cost side when weighing any monetisation upside the data cannot show.",
         impact=f"Plausible range {abs(hi)*1000:,.0f} to {abs(lo)*1000:,.0f} per 100,000 (from the confidence interval). Revenue was not measured."),
    dict(num=f"{heavy.diff_pp:.2f} pp",
         what=f"The loss concentrates in heavy players (more than the median rounds): {heavy.diff_pp:.2f} pp, p = {heavy.p:.4f}; light players show {light.diff_pp:.2f} pp (p = {light.p:.2f}).",
         action="If a later gate is revisited, look at engaged players first. Treat this as a lead, not a finding.",
         impact="Rounds are measured after assignment, so the segment is descriptive only."),
    dict(num=f"SRM p = {d['srm_p']:.4f}",
         what=f"Group sizes are {d['n_control']:,} vs {d['n_treatment']:,}, a sample-ratio warning, and the placebo group (under 30 rounds) also differs ({placebo.diff_pp:.2f} pp, p = {placebo.p:.3f}).",
         action="Ask how players were assigned before trusting any follow-up test; rerun with a balanced split.",
         impact="The result deserves slightly less trust than a perfectly balanced test. It passes the pre-set stop threshold (p < 0.001)."),
    dict(num=f"{pw['mde_7_pp']:.2f} pp detectable",
         what=f"The test could detect a 7-day gap of about {pw['mde_7_pp']:.2f} pp (80% power). 1-day retention (p = {p1['p']:.3f}) and game rounds (p = {gr['p']:.4f}) are not significant or only borderline.",
         action="In the next test add revenue and longer-term retention as metrics and size it for a smaller effect.",
         impact=f"The observed {abs(p7['diff_pp']):.2f} pp gap sits just above the detectable limit, so the finding is real but with little margin."),
]

v7 = byv[byv.metric == "retention_7"].set_index("version")
f1 = go.Figure()
for v, col in [("gate_30", BLUE), ("gate_40", ORANGE)]:
    r = v7.loc[v]
    f1.add_bar(x=[v], y=[r.rate * 100], name=v, marker_color=col,
               error_y=dict(type="data", symmetric=False, array=[(r.ci_high - r.rate) * 100], arrayminus=[(r.rate - r.ci_low) * 100]),
               text=[f"{r.rate*100:.2f}%"], textposition="outside", hovertemplate=f"{v}: %{{y:.2f}}% (n={int(r.players):,})<extra></extra>")
f1.update_yaxes(title="7-day retention, % (95% CI)", range=[0, 24])
style(f1, 340)

f2 = go.Figure()
rows = [("7-day retention (primary)", p7["diff_pp"], p7["ci_analytic_pp"][0], p7["ci_analytic_pp"][1]),
        ("1-day retention", p1["diff_pp"], p1["ci_bootstrap_pp"][0], p1["ci_bootstrap_pp"][1])]
for _, r in seg.iterrows():
    rows.append((r.segment, r.diff_pp, r.ci_low_pp, r.ci_high_pp))
fd = pd.DataFrame(rows, columns=["name", "diff", "lo", "hi"]).iloc[::-1]
f2.add_trace(go.Scatter(x=fd["diff"], y=fd["name"], mode="markers", marker=dict(size=10, color=[ORANGE if h < 0 else BLUE for h in fd.hi]),
                        error_x=dict(type="data", symmetric=False, array=fd.hi - fd["diff"], arrayminus=fd["diff"] - fd.lo, color=MUTED),
                        hovertemplate="%{y}: %{x:.2f} pp<extra></extra>"))
f2.add_vline(x=0, line_dash="dot", line_color=MUTED)
f2.update_xaxes(title="Difference, gate_40 minus gate_30 (percentage points, 95% CI)")
style(f2, 380, False)
f2.update_layout(margin=dict(l=300, r=24, t=16, b=48))

b7 = bkt[bkt.metric == "retention_7"].sort_values("bucket_order")
f3 = go.Figure()
for v, col in [("gate_30", BLUE), ("gate_40", ORANGE)]:
    b = b7[b7.version == v]
    f3.add_scatter(x=b.rounds_bucket, y=b.rate * 100, mode="lines+markers", name=v, line=dict(color=col, width=2), marker=dict(size=8),
                   error_y=dict(type="data", symmetric=False, array=(b.ci_high - b.rate) * 100, arrayminus=(b.rate - b.ci_low) * 100),
                   hovertemplate=v + " %{x} rounds: %{y:.1f}%<extra></extra>")
f3.update_xaxes(title="Game rounds in first 14 days", type="category")
f3.update_yaxes(title="7-day retention, %")
style(f3, 380)

sections = [
    ("Primary metric", "7-day retention by version with 95% confidence intervals.", f1),
    ("Every comparison on one axis", "Difference in percentage points with 95% CI. Orange = interval entirely below zero. Segments are exploratory.", f2),
    ("7-day retention by engagement", "By number of game rounds played (bucket), both versions. Rounds are measured after assignment, so descriptive only.", f3),
]
out, size = build_page(
    "SplitTest Lab: should Cookie Cats move its first gate to level 40?",
    "A/B test of 90,189 Cookie Cats players (public Kaggle dataset, retrospective analysis, not pre-registered). Decision rule written before the analysis.",
    insights, sections,
    caveat="Mild sample-ratio warning (p = 0.0086) and a borderline placebo difference suggest something besides the gate may contribute. Retention only: no revenue was available.",
    footer="Every number comes from results/ab_summary.json, results/segments.csv and tableau/*.csv. Method: README and memo.md. Interactive Tableau version linked in the README.",
    out=str(OUT / "index.html"), offline="--offline" in sys.argv)
print("wrote", out, f"{size/1e6:.2f} MB")
if "--png" in sys.argv:
    (OUT / "img").mkdir(exist_ok=True)
    screenshot(out, OUT / "img" / "report-top.png", height=1100)
    screenshot(out, OUT / "img" / "report-full.png", full=True)
