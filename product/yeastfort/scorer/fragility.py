"""
Fragility scorer.

Given a user protocol, run N Monte Carlo simulations and compute:
  - overall_fragility (0-100, higher = more fragile)
  - shock_survival   (0-100, higher = better)
  - reproducibility  (0-100, higher = more consistent run-to-run)
  - recovery         (0-100, higher = better post-shock recovery)

Plus diagnostic data the UI can plot.

The user never sees the ABM. They see scores and a single chart.
"""

from __future__ import annotations
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent.parent.parent  # scorer -> yeastfort -> product -> repo
V01_SRC = _REPO_ROOT / "v0.1" / "src"
sys.path.insert(0, str(V01_SRC))
sys.path.insert(0, str(_HERE))

from dataclasses import dataclass, field
from typing import Optional
import numpy as np
import pandas as pd

from bioreactor import BioreactorModel
from protocol_env import ProtocolEnvironment


@dataclass
class FragilityReport:
    overall_fragility: float            # 0 (robust) – 100 (fragile)
    shock_survival: float               # 0–100
    reproducibility: float              # 0–100
    recovery: float                     # 0–100
    extinction_rate: float              # 0–1
    final_biomass_p10: float
    final_biomass_p50: float
    final_biomass_p90: float
    n_seeds: int
    bimodality_index: float             # 0 = unimodal, 1 = perfectly bimodal
    weak_points: list[str] = field(default_factory=list)
    # raw per-seed outcomes so the UI can draw the histogram
    per_seed: pd.DataFrame = field(default_factory=pd.DataFrame)
    # mean trajectory across seeds
    mean_trajectory: pd.DataFrame = field(default_factory=pd.DataFrame)


def _run_one(schedule: pd.DataFrame, seed: int, ticks: int) -> dict:
    """One simulation; returns final-state + trajectory summary."""
    m = BioreactorModel(env_kind="constant", seed=seed)  # placeholder env
    # Overwrite with the user's protocol-driven environment
    m.env = ProtocolEnvironment(
        schedule=schedule,
        rng=m.random_np_generator(),
        black_swan=True,
    )
    df = m.run(ticks)
    final = df.iloc[-1]
    swan = m.env.swan_tick
    pre_swan_alive = int(df.loc[max(0, swan - 1), "alive"]) if swan else None
    post_swan_min = int(df.loc[swan:, "alive"].min()) if swan else None
    final_alive = int(final["alive"])
    recovered = (
        post_swan_min > 0 and final_alive >= 0.5 * pre_swan_alive
        if (swan and pre_swan_alive) else False
    )
    return {
        "seed": seed,
        "final_alive": final_alive,
        "final_biomass": float(final["biomass"]),
        "extinct": final_alive == 0,
        "swan_tick": swan,
        "pre_swan_alive": pre_swan_alive,
        "post_swan_min": post_swan_min,
        "recovered": recovered,
        "trajectory_alive": df["alive"].values.tolist(),
    }


def _bimodality_index(values: np.ndarray) -> float:
    """Crude bimodality measure: fraction of mass in the tails (excluding the
    middle quintile) of the distribution. 0 = unimodal mass in the center,
    ~1 = mass concentrated at both ends. Reproducibility crisis signature.

    We use a normalized version that ignores degenerate (all-zero) cases.
    """
    if len(values) < 5:
        return 0.0
    v = np.asarray(values, dtype=float)
    if v.max() == v.min():
        return 0.0
    # Normalize to [0, 1]
    vn = (v - v.min()) / (v.max() - v.min())
    # Fraction of points in the two outer 25% bins, vs middle 50%
    outer = ((vn < 0.25) | (vn > 0.75)).mean()
    # Pure unimodal centered: outer ~= 0.5; perfectly bimodal: outer = 1.
    return float(np.clip((outer - 0.5) * 2, 0, 1))


def score_protocol(
    schedule: pd.DataFrame,
    n_seeds: int = 80,
    ticks: int = 150,
    progress_cb=None,
) -> FragilityReport:
    """Main entry point. Optionally calls progress_cb(i, n_seeds)."""
    rows = []
    trajectories = []
    for i in range(n_seeds):
        rows.append(_run_one(schedule, seed=i, ticks=ticks))
        trajectories.append(rows[-1]["trajectory_alive"])
        if progress_cb is not None:
            progress_cb(i + 1, n_seeds)
    df = pd.DataFrame(rows)

    extinction_rate = float(df["extinct"].mean())
    biomass = df["final_biomass"].values
    p10, p50, p90 = (
        float(np.percentile(biomass, 10)),
        float(np.percentile(biomass, 50)),
        float(np.percentile(biomass, 90)),
    )
    bm_idx = _bimodality_index(biomass)

    # --- Subscores ---
    # Shock survival: fraction of runs that survived (alive > 0)
    shock_survival = (1 - extinction_rate) * 100

    # Reproducibility: inverse of coefficient-of-variation, capped.
    # If everyone dies, technically reproducible — but worthless.
    # We compute reproducibility AMONG survivors only, then penalize by
    # the share of runs that died (you can't reproduce extinction).
    survivors = biomass[biomass > 0]
    if len(survivors) >= 3:
        cv = survivors.std() / max(survivors.mean(), 1e-9)
        survivor_repro = float(np.clip(100 * (1 - cv), 0, 100))
    else:
        survivor_repro = 0.0
    reproducibility = survivor_repro * (1 - extinction_rate)

    # Recovery: of those that experienced a swan, what fraction recovered?
    swan_runs = df[df["swan_tick"].notna()]
    if len(swan_runs):
        recovery = float(swan_runs["recovered"].mean()) * 100
    else:
        recovery = 0.0

    # Overall fragility: weighted combination, higher = worse
    overall = 100 - (
        0.5 * shock_survival +
        0.3 * reproducibility +
        0.2 * recovery
    )
    overall = float(np.clip(overall, 0, 100))

    # --- Heuristic weak points (explanation users can act on) ---
    weak = []
    if extinction_rate > 0.6:
        weak.append("High extinction rate under contamination shock — the "
                    "protocol's safety margin is thin.")
    if bm_idx > 0.6:
        weak.append(f"Outcome distribution is strongly bimodal "
                    f"(index={bm_idx:.2f}) — runs either succeed fully or "
                    "crash entirely. This is the classic reproducibility-crisis "
                    "signature.")
    if recovery < 30 and len(swan_runs) > 0:
        weak.append("Once stress hits, the population rarely recovers. "
                    "Consider adding hormetic priming earlier in the run.")
    sched = schedule.sort_values("tick")
    if sched["temperature"].std() < 0.5:
        weak.append("Temperature is essentially constant. Pulsed mild heat "
                    "shocks (35–37 °C for short windows) often improve robustness.")
    if sched["glucose_feed"].std() < 0.5:
        weak.append("Feed rate is essentially constant. Pulsed feeding "
                    "(feast–famine) may increase stress-response priming.")
    if not weak:
        weak.append("No major weak points detected at this confidence level.")

    # Mean trajectory across seeds
    T = max(len(t) for t in trajectories)
    arr = np.full((len(trajectories), T), np.nan)
    for i, t in enumerate(trajectories):
        arr[i, :len(t)] = t
    mean_traj = pd.DataFrame({
        "tick": np.arange(T),
        "alive_mean": np.nanmean(arr, axis=0),
        "alive_p10": np.nanpercentile(arr, 10, axis=0),
        "alive_p90": np.nanpercentile(arr, 90, axis=0),
    })

    return FragilityReport(
        overall_fragility=overall,
        shock_survival=shock_survival,
        reproducibility=reproducibility,
        recovery=recovery,
        extinction_rate=extinction_rate,
        final_biomass_p10=p10,
        final_biomass_p50=p50,
        final_biomass_p90=p90,
        n_seeds=n_seeds,
        bimodality_index=bm_idx,
        weak_points=weak,
        per_seed=df.drop(columns=["trajectory_alive"]),
        mean_trajectory=mean_traj,
    )
