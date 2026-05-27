"""
Recommender core.

For each candidate schedule, run N Monte Carlo simulations of the v0.1
ABM and compute:
  - yield_mean      : average final biomass across seeds (the headline)
  - yield_p10       : 10th-percentile yield (downside risk)
  - yield_p90       : 90th-percentile yield (upside)
  - extinction_rate : fraction of runs that ended in total crash
  - reliability     : fraction of runs with yield > 25% of best-case mean

The "yield" objective ranks by `yield_mean`, but downside metrics are
shown alongside so a user choosing #1 vs #2 can see the trade-off.

Honest-label reminder: the underlying ABM is a generic toy. Rankings
have meaning only inside this model — see the warning banner in the UI.
"""

from __future__ import annotations
import sys
from pathlib import Path
from dataclasses import dataclass, field

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT / "v0.1" / "src"))
sys.path.insert(0, str(_REPO_ROOT / "product" / "yeastfort" / "scorer"))

import numpy as np
import pandas as pd

from bioreactor import BioreactorModel
from protocol_env import ProtocolEnvironment
from schedules import Candidate, generate_all
from statistics import compare_to_top, ComparisonResult


@dataclass
class EvaluationResult:
    candidate: Candidate
    yield_mean: float
    yield_median: float
    yield_p10: float
    yield_p90: float
    yield_std: float
    extinction_rate: float
    reliability: float        # fraction with yield > 25% of max-mean
    n_seeds: int
    per_seed_yields: np.ndarray = field(default_factory=lambda: np.array([]))


def _evaluate_one(candidate: Candidate, n_seeds: int, ticks: int,
                  black_swan: bool) -> EvaluationResult:
    yields = []
    extinct_count = 0
    for seed in range(n_seeds):
        m = BioreactorModel(env_kind="constant", seed=seed)
        m.env = ProtocolEnvironment(
            schedule=candidate.schedule,
            rng=m.random_np_generator(),
            black_swan=black_swan,
        )
        df = m.run(ticks)
        final = df.iloc[-1]
        yields.append(float(final["biomass"]))
        if int(final["alive"]) == 0:
            extinct_count += 1
    arr = np.asarray(yields)
    return EvaluationResult(
        candidate=candidate,
        yield_mean=float(arr.mean()),
        yield_median=float(np.median(arr)),
        yield_p10=float(np.percentile(arr, 10)),
        yield_p90=float(np.percentile(arr, 90)),
        yield_std=float(arr.std()),
        extinction_rate=extinct_count / n_seeds,
        reliability=0.0,   # filled in below once we know the best-case
        n_seeds=n_seeds,
        per_seed_yields=arr,
    )


def evaluate_all(
    candidates: list[Candidate],
    n_seeds: int = 40,
    ticks: int = 150,
    black_swan: bool = True,
    progress_cb=None,
) -> list[EvaluationResult]:
    """Evaluate every candidate. Returns results ordered as candidates were."""
    results = []
    total = len(candidates)
    for i, c in enumerate(candidates):
        results.append(_evaluate_one(c, n_seeds, ticks, black_swan))
        if progress_cb is not None:
            progress_cb(i + 1, total, c.name)

    # Reliability is computed relative to the best-case yield across all
    # candidates — a candidate is "reliable" if at least 25% of the best
    # achievable yield is hit in a given run.
    best_mean = max(r.yield_mean for r in results) if results else 1.0
    threshold = 0.25 * best_mean
    for r in results:
        r.reliability = float((r.per_seed_yields > threshold).mean())
    return results


def evaluate_and_compare(
    candidates: list[Candidate],
    n_seeds: int = 40,
    ticks: int = 150,
    black_swan: bool = True,
    progress_cb=None,
) -> tuple[list[EvaluationResult], ComparisonResult]:
    """Full pipeline: evaluate all candidates, then statistically compare them.

    Returns the evaluation list (raw) and a ComparisonResult covering all
    candidates. Order of the evaluation list is preserved; ComparisonResult
    is indexed against that order.
    """
    results = evaluate_all(
        candidates, n_seeds=n_seeds, ticks=ticks,
        black_swan=black_swan, progress_cb=progress_cb,
    )
    yields_lists = [r.per_seed_yields for r in results]
    comparison = compare_to_top(yields_lists)
    return results, comparison


def rank_by_yield(results: list[EvaluationResult]) -> list[EvaluationResult]:
    """Return results sorted descending by yield_mean."""
    return sorted(results, key=lambda r: -r.yield_mean)


def summary_table(results: list[EvaluationResult]) -> pd.DataFrame:
    """Build a tabular summary for the UI."""
    rows = []
    for r in results:
        rows.append({
            "name": r.candidate.name,
            "label": r.candidate.short_label(),
            "pattern": r.candidate.pattern,
            "yield_mean": r.yield_mean,
            "yield_median": r.yield_median,
            "yield_p10": r.yield_p10,
            "yield_p90": r.yield_p90,
            "extinction_rate": r.extinction_rate,
            "reliability": r.reliability,
            "n_seeds": r.n_seeds,
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    import time
    cs = generate_all()
    print(f"Evaluating {len(cs)} candidates with 30 seeds each "
          f"(~{len(cs)*30*0.2:.0f}s)...")
    t0 = time.time()
    rs = evaluate_all(cs, n_seeds=30, ticks=130)
    rs_ranked = rank_by_yield(rs)
    print(f"\nDone in {time.time()-t0:.1f}s.\n")
    df = summary_table(rs_ranked)
    print(df[["name", "yield_mean", "yield_p10",
              "extinction_rate", "reliability"]].to_string(index=False))
