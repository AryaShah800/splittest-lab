"""Statistics for an A/B test, written out explicitly so every formula can be explained and unit-tested."""
import numpy as np
from scipy import stats


def srm_check(n_a: int, n_b: int, expected_share_a: float = 0.5) -> dict:
    """Sample ratio mismatch: chi-square goodness of fit of the observed group sizes against the planned split.

    A very small p-value (conventionally < 0.001) means the assignment did not produce the planned split, so the
    experiment should be investigated before any effect is interpreted.
    """
    if not 0 < expected_share_a < 1:
        raise ValueError("expected_share_a must be between 0 and 1")
    total = n_a + n_b
    expected = [total * expected_share_a, total * (1 - expected_share_a)]
    chi2, p = stats.chisquare([n_a, n_b], f_exp=expected)
    return {"chi2": float(chi2), "p_value": float(p), "share_a": n_a / total}


def two_proportion_ztest(x_a: int, n_a: int, x_b: int, n_b: int) -> dict:
    """Two-sided z-test that two proportions are equal (pooled standard error), plus the Wald 95% CI on b - a.

    Returns the difference as (rate_b - rate_a), so a positive value means group B is higher.
    """
    if min(n_a, n_b) <= 0:
        raise ValueError("group sizes must be positive")
    if not (0 <= x_a <= n_a and 0 <= x_b <= n_b):
        raise ValueError("successes must be between 0 and the group size")
    p_a, p_b = x_a / n_a, x_b / n_b
    pooled = (x_a + x_b) / (n_a + n_b)
    se_pooled = np.sqrt(pooled * (1 - pooled) * (1 / n_a + 1 / n_b))
    z = (p_b - p_a) / se_pooled if se_pooled > 0 else 0.0
    p_value = 2 * stats.norm.sf(abs(z))
    se_unpooled = np.sqrt(p_a * (1 - p_a) / n_a + p_b * (1 - p_b) / n_b)
    half = stats.norm.ppf(0.975) * se_unpooled
    diff = p_b - p_a
    return {"rate_a": p_a, "rate_b": p_b, "diff": diff, "z": float(z), "p_value": float(p_value),
            "ci_low": float(diff - half), "ci_high": float(diff + half)}


def bootstrap_proportion_diff_ci(x_a: int, n_a: int, x_b: int, n_b: int, n_boot: int = 20000,
                                 seed: int = 0, level: float = 0.95) -> dict:
    """Percentile bootstrap CI for (rate_b - rate_a).

    Resampling a 0/1 outcome with replacement is exactly equivalent to drawing Binomial(n, observed rate), so the
    binomial draw is used. It gives the same distribution as resampling the rows and is far faster on ~45k rows per arm.
    """
    rng = np.random.default_rng(seed)
    boot_a = rng.binomial(n_a, x_a / n_a, size=n_boot) / n_a
    boot_b = rng.binomial(n_b, x_b / n_b, size=n_boot) / n_b
    diffs = boot_b - boot_a
    tail = (1 - level) / 2
    lo, hi = np.quantile(diffs, [tail, 1 - tail])
    return {"diff": x_b / n_b - x_a / n_a, "ci_low": float(lo), "ci_high": float(hi), "n_boot": n_boot}


def mde_two_proportions(n_a: int, n_b: int, baseline_rate: float, alpha: float = 0.05, power: float = 0.8) -> float:
    """Minimum detectable absolute difference in a proportion (two-sided test, normal approximation).

    Uses the unpooled standard error at the baseline rate. It answers: how big would a true difference have to be
    for this sample to detect it with the stated power?
    """
    if not 0 < baseline_rate < 1:
        raise ValueError("baseline_rate must be between 0 and 1")
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_power = stats.norm.ppf(power)
    se = np.sqrt(baseline_rate * (1 - baseline_rate) * (1 / n_a + 1 / n_b))
    return float((z_alpha + z_power) * se)


def mann_whitney(a, b) -> dict:
    """Two-sided Mann-Whitney U test (for skewed counts such as game rounds) with medians and the common-language effect."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    res = stats.mannwhitneyu(a, b, alternative="two-sided")
    # Probability that a random draw from a is larger than one from b (ties count half): U_a / (n_a * n_b)
    prob_a_larger = float(res.statistic / (len(a) * len(b)))
    return {"u": float(res.statistic), "p_value": float(res.pvalue), "median_a": float(np.median(a)),
            "median_b": float(np.median(b)), "prob_a_larger": prob_a_larger}


def bonferroni_threshold(alpha: float, n_comparisons: int) -> float:
    """Per-comparison significance threshold when running several exploratory tests."""
    if n_comparisons < 1:
        raise ValueError("n_comparisons must be at least 1")
    return alpha / n_comparisons
