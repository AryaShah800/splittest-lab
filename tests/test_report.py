"""Headline numbers on the report cards must equal values recomputed from the source result files."""
import json
import subprocess
import sys
from pathlib import Path
import pandas as pd
import pytest

pytest.importorskip("plotly")
R = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def page(tmp_path_factory):
    out = tmp_path_factory.mktemp("report")
    subprocess.run([sys.executable, str(R / "scripts" / "build_report.py"), "--out", str(out)], check=True, cwd=R)
    return (out / "index.html").read_text(encoding="utf-8")


def test_findings_come_before_charts(page):
    assert page.index("Key findings") < page.index('id="c0"')


def test_headline_numbers_match_sources(page):
    s = json.load(open(R / "results" / "ab_summary.json"))
    p7 = s["primary_retention_7"]
    seg = pd.read_csv(R / "results" / "segments.csv")
    heavy = seg[seg.segment.str.startswith("heavy")].iloc[0]
    lo, hi = p7["ci_analytic_pp"]
    for e in [f"{p7['diff_pp']:.2f} pp", f"{p7['rate_control']*100:.2f}%", f"{p7['rate_treatment']*100:.2f}%",
              f"p = {p7['p']:.4f}", f"{lo:.2f} to {hi:.2f} pp", f"{heavy.diff_pp:.2f} pp",
              f"SRM p = {s['design']['srm_p']:.4f}", f"{s['power']['mde_7_pp']:.2f} pp detectable"]:
        assert e in page, e


def test_tableau_csv_agrees_with_summary():
    s = json.load(open(R / "results" / "ab_summary.json"))
    v = pd.read_csv(R / "tableau" / "retention_by_version.csv")
    r = v[(v.version == "gate_30") & (v.metric == "retention_7")].rate.iloc[0]
    assert abs(r - s["primary_retention_7"]["rate_control"]) < 1e-12
