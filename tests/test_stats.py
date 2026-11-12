"""Unit tests for splittest.stats. Reference values are hand-derived or cross-checked against statsmodels."""
import numpy as np
import pytest
from statsmodels.stats.proportion import proportions_ztest

from splittest import stats as s


def test_ztest_matches_hand_calculation():
    # 30/100 vs 45/100: pooled p = 0.375, SE = sqrt(0.375 * 0.625 * 0.02) = 0.068465, z = 0.15 / 0.068465 = 2.1909
    r = s.two_proportion_ztest(30, 100, 45, 100)
    assert r["diff"] == pytest.approx(0.15)
    assert r["z"] == pytest.approx(2.1909, abs=1e-3)
    assert r["p_value"] == pytest.approx(0.02846, abs=1e-4)


def test_ztest_agrees_with_statsmodels_on_large_samples():
    x_a, n_a, x_b, n_b = 8_410, 44_700, 8_220, 45_489
    mine = s.two_proportion_ztest(x_a, n_a, x_b, n_b)
    z_ref, p_ref = proportions_ztest([x_b, x_a], [n_b, n_a])  # statsmodels: first group minus second
    assert mine["z"] == pytest.approx(z_ref, rel=1e-9)
    assert mine["p_value"] == pytest.approx(p_ref, rel=1e-9)


def test_ztest_no_difference_gives_p_of_one():
    r = s.two_proportion_ztest(50, 1000, 50, 1000)
    assert r["diff"] == 0 and r["p_value"] == pytest.approx(1.0)


def test_ztest_sign_follows_group_b_minus_a():
    assert s.two_proportion_ztest(10, 100, 30, 100)["diff"] > 0
    assert s.two_proportion_ztest(30, 100, 10, 100)["diff"] < 0


def test_ztest_confidence_interval_contains_the_difference():
    r = s.two_proportion_ztest(30, 100, 45, 100)
    assert r["ci_low"] < r["diff"] < r["ci_high"]


@pytest.mark.parametrize("args", [(5, 0, 5, 10), (11, 10, 5, 10), (-1, 10, 5, 10)])
def test_ztest_rejects_invalid_input(args):
    with pytest.raises(ValueError):
        s.two_proportion_ztest(*args)


def test_srm_perfect_split():
    r = s.srm_check(5000, 5000)
    assert r["chi2"] == pytest.approx(0.0) and r["p_value"] == pytest.approx(1.0)


def test_srm_detects_a_broken_split():
    # expected 5000 each; (500^2 / 5000) * 2 = 100
    r = s.srm_check(4500, 5500)
    assert r["chi2"] == pytest.approx(100.0)
    assert r["p_value"] < 1e-20


def test_srm_respects_a_non_even_planned_split():
    assert s.srm_check(900, 100, expected_share_a=0.9)["p_value"] == pytest.approx(1.0)


def test_srm_rejects_invalid_share():
    with pytest.raises(ValueError):
        s.srm_check(10, 10, expected_share_a=1.0)


def test_bootstrap_is_reproducible_with_a_seed():
    a = s.bootstrap_proportion_diff_ci(200, 1000, 260, 1000, n_boot=2000, seed=7)
    b = s.bootstrap_proportion_diff_ci(200, 1000, 260, 1000, n_boot=2000, seed=7)
    assert a == b


def test_bootstrap_interval_is_close_to_the_analytic_interval():
    x_a, n_a, x_b, n_b = 8_410, 44_700, 8_220, 45_489
    boot = s.bootstrap_proportion_diff_ci(x_a, n_a, x_b, n_b, n_boot=20_000, seed=1)
    wald = s.two_proportion_ztest(x_a, n_a, x_b, n_b)
    assert boot["ci_low"] == pytest.approx(wald["ci_low"], abs=5e-4)
    assert boot["ci_high"] == pytest.approx(wald["ci_high"], abs=5e-4)
    assert boot["ci_low"] < boot["diff"] < boot["ci_high"]


def test_bootstrap_interval_covers_zero_when_there_is_no_effect():
    r = s.bootstrap_proportion_diff_ci(500, 5000, 500, 5000, n_boot=5000, seed=3)
    assert r["ci_low"] < 0 < r["ci_high"]


def test_mde_matches_the_closed_form():
    # (1.959964 + 0.841621) * sqrt(0.2 * 0.8 * (1/10000 + 1/10000)) = 0.015849
    assert s.mde_two_proportions(10_000, 10_000, 0.2) == pytest.approx(0.015849, rel=1e-3)


def test_mde_shrinks_with_more_data_and_grows_with_more_power():
    assert s.mde_two_proportions(40_000, 40_000, 0.2) < s.mde_two_proportions(10_000, 10_000, 0.2)
    assert s.mde_two_proportions(10_000, 10_000, 0.2, power=0.9) > s.mde_two_proportions(10_000, 10_000, 0.2, power=0.8)


def test_mde_quadrupling_the_sample_halves_it():
    small = s.mde_two_proportions(10_000, 10_000, 0.2)
    assert s.mde_two_proportions(40_000, 40_000, 0.2) == pytest.approx(small / 2, rel=1e-9)


def test_mann_whitney_separated_samples():
    r = s.mann_whitney(np.arange(100), np.arange(100, 200))
    assert r["u"] == 0 and r["prob_a_larger"] == 0.0
    assert r["p_value"] < 1e-20
    assert r["median_a"] == 49.5 and r["median_b"] == 149.5


def test_mann_whitney_identical_samples_have_no_effect():
    r = s.mann_whitney(np.arange(50), np.arange(50))
    assert r["p_value"] == pytest.approx(1.0)
    assert r["prob_a_larger"] == pytest.approx(0.5)


def test_bonferroni_threshold():
    assert s.bonferroni_threshold(0.05, 5) == pytest.approx(0.01)
    with pytest.raises(ValueError):
        s.bonferroni_threshold(0.05, 0)
