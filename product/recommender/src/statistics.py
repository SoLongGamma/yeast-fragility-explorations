"""
Statistical comparison utilities for ranking candidates.

The naive "winner = highest mean" answer is misleading when comparing
many candidates with noisy Monte Carlo estimates. Following Taleb (2024,
"Data Hacking Distribution and Multiple Trials"), we treat the ranking
as a multiple-comparison problem and report which candidates are
*statistically indistinguishable* from the top.

We use two complementary methods:

  1. **Bootstrap confidence intervals** on each candidate's mean yield.
     Two candidates are "tied" if their 95% CIs overlap.

  2. **Welch's t-test with Bonferroni correction** between the top and
     each other candidate. Tied if adjusted p > 0.05.

The UI then communicates this honestly: the user is shown that #1 isn't
"the answer" but rather "one of K plausible answers" — where K is often
larger than they'd guess.

This is not a substitute for wet-lab validation. It is a guard against
manufacturing apparent significance through repeated comparison.
"""

from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from scipy import stats


N_BOOTSTRAP = 2000
CI_LEVEL = 0.95
ALPHA = 0.05


@dataclass
class ComparisonResult:
    """Result of comparing all candidates against the top performer."""
    top_index: int                       # index of #1 by raw mean
    bootstrap_means: np.ndarray          # shape (n_candidates, N_BOOTSTRAP)
    ci_lo: np.ndarray                    # shape (n_candidates,)
    ci_hi: np.ndarray                    # shape (n_candidates,)
    p_values_vs_top: np.ndarray          # raw two-sided p-values
    p_adjusted: np.ndarray               # Bonferroni-corrected
    tied_with_top: np.ndarray            # bool mask
    significantly_worse: np.ndarray      # bool mask


def bootstrap_mean_distribution(samples: np.ndarray,
                                n_boot: int = N_BOOTSTRAP,
                                rng: np.random.Generator | None = None
                                ) -> np.ndarray:
    """Return n_boot resampled means of `samples`."""
    if rng is None:
        rng = np.random.default_rng(0)
    n = len(samples)
    if n == 0:
        return np.zeros(n_boot)
    # Vectorized bootstrap
    idx = rng.integers(0, n, size=(n_boot, n))
    return samples[idx].mean(axis=1)


def confidence_interval(boot_means: np.ndarray,
                        level: float = CI_LEVEL) -> tuple[float, float]:
    alpha = (1 - level) / 2
    return (float(np.quantile(boot_means, alpha)),
            float(np.quantile(boot_means, 1 - alpha)))


def compare_to_top(yields_per_candidate: list[np.ndarray],
                   alpha: float = ALPHA,
                   rng: np.random.Generator | None = None
                   ) -> ComparisonResult:
    """
    Run the full comparison battery.

    Parameters
    ----------
    yields_per_candidate
        List of arrays. Each array contains the per-seed yields for one
        candidate schedule.
    alpha
        Significance level *before* Bonferroni adjustment.

    Returns
    -------
    ComparisonResult with per-candidate CI, tied-with-top flags, etc.
    """
    if rng is None:
        rng = np.random.default_rng(42)

    n_cand = len(yields_per_candidate)
    means = np.array([y.mean() for y in yields_per_candidate])
    top_idx = int(np.argmax(means))
    top_samples = yields_per_candidate[top_idx]

    # Bootstrap each candidate
    boots = np.stack([
        bootstrap_mean_distribution(y, rng=rng)
        for y in yields_per_candidate
    ])
    ci_lo = np.array([confidence_interval(b)[0] for b in boots])
    ci_hi = np.array([confidence_interval(b)[1] for b in boots])

    # Welch's t-test vs top
    p_raw = np.zeros(n_cand)
    for i, y in enumerate(yields_per_candidate):
        if i == top_idx:
            p_raw[i] = 1.0
            continue
        # If either has zero variance (e.g., all extinct), fall back to
        # comparing means directly without t-test
        if y.std() == 0 and top_samples.std() == 0:
            p_raw[i] = 0.0 if y.mean() < top_samples.mean() else 1.0
            continue
        try:
            t_stat, p = stats.ttest_ind(top_samples, y, equal_var=False)
            p_raw[i] = float(p)
        except Exception:
            p_raw[i] = 1.0

    # Bonferroni correction: multiply by number of comparisons (n_cand - 1)
    n_comparisons = max(n_cand - 1, 1)
    p_adj = np.minimum(p_raw * n_comparisons, 1.0)

    # "Tied" = either CI overlaps top's CI, OR Bonferroni-adjusted p > alpha
    top_ci_lo, top_ci_hi = ci_lo[top_idx], ci_hi[top_idx]
    ci_overlap = (ci_lo <= top_ci_hi) & (ci_hi >= top_ci_lo)
    ttest_tied = p_adj > alpha
    tied = ci_overlap | ttest_tied
    tied[top_idx] = True  # top is trivially tied with itself

    sig_worse = ~tied

    return ComparisonResult(
        top_index=top_idx,
        bootstrap_means=boots,
        ci_lo=ci_lo,
        ci_hi=ci_hi,
        p_values_vs_top=p_raw,
        p_adjusted=p_adj,
        tied_with_top=tied,
        significantly_worse=sig_worse,
    )


def search_inflation_warning(n_trials: int, ensemble_std: float) -> dict:
    """
    Estimate how much of the apparent best-of-N improvement comes from
    *pure noise* rather than true effect.

    This is the simplest possible operationalization of Taleb's
    Proposition 3 (distribution of the minimum/maximum of m
    statistically-identical trials). The exact distribution from Taleb's
    paper requires assuming p-values; here we use the simpler Gaussian
    extreme-value approximation since we work with yields directly.

    Returns a dict with:
      expected_max_under_null : expected max of N i.i.d. N(0, sigma^2)
      caveat                  : human-readable warning

    The intent is to display this *next to* the user's reported "best
    yield so far" so they can see how much of their apparent improvement
    is search-noise.
    """
    if n_trials < 2:
        return {
            "expected_max_under_null": 0.0,
            "caveat": "Too few trials to estimate search inflation.",
        }
    # Gaussian extreme-value approximation: E[max] ≈ sigma * sqrt(2 ln N)
    # for N i.i.d. standard normals; scaled by ensemble_std.
    expected_max = ensemble_std * np.sqrt(2 * np.log(n_trials))
    return {
        "expected_max_under_null": float(expected_max),
        "n_trials": n_trials,
        "ensemble_std": float(ensemble_std),
        "caveat": (
            f"With {n_trials} trials of ensemble std {ensemble_std:.1f}, "
            f"pure search noise alone could produce an apparent best-trial "
            f"improvement of about {expected_max:.1f} above the mean. "
            f"Real improvements should clearly exceed this."
        ),
    }
