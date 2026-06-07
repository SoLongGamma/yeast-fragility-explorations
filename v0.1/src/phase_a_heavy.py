"""
Phase A — heavy run on user's machine (not the analysis container).

This script extends v0.1's ABM with proper input-variance injection so we
can apply Axenie et al. (2025)'s antifragility framework correctly.

Two axes of variation are now separated:

  1. INPUT VARIANCE  (Axenie's σ): per-trial perturbations to the cell
     population's *starting condition* and *environment parameters*. This
     is the "lab-to-lab variability" the Axenie framework analyzes.

  2. SHOCK SEVERITY  (swan_scale): a separate axis — the magnitude of the
     black-swan event when it fires. Not the same as Axenie's σ.

This distinction was missed in the pilot run, where swan_scale was
incorrectly used as if it were Axenie's σ. We keep both axes here so we
can sweep each independently.

OUTPUT
------
Two CSV files are written to the working directory:
  - phase_a_raw.csv      one row per (schedule, sigma, swan_scale, seed)
  - phase_a_metrics.csv  one row per (schedule, sigma, swan_scale)

HOW TO RUN
----------
1. Clone or download the project repo:
       git clone https://github.com/SoLongGamma/yeast-fragility-explorations.git
2. cd into v0.1/src so this script's imports work:
       cd yeast-fragility-explorations/v0.1/src
3. Install requirements (one-time):
       pip install mesa numpy pandas scipy
4. Place this script next to bioreactor.py and run:
       python phase_a_heavy.py --n 500 --sigmas 0.05 0.1 0.2 --swan_scales 2.5
5. Output appears in ./phase_a_raw.csv and ./phase_a_metrics.csv.

TIME ESTIMATE
-------------
On an M-series Mac:
  - N=100   per (schedule × σ × swan_scale)  ≈ 1–2 min per cell
  - N=500   per cell                          ≈ 5–10 min per cell
  - N=2000  per cell                          ≈ 30–60 min per cell
For 2 schedules × 3 σ × 2 swan_scales × N=500 → about 1–2 hours.

The default parameters below give a moderate "overnight" run.
Change them with command-line flags if you want shorter or longer.
"""

from __future__ import annotations
import argparse
import os
import sys
import time
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats


# Make the v0.1 source importable regardless of how the script is invoked.
HERE = Path(__file__).resolve().parent
if (HERE / "bioreactor.py").exists():
    sys.path.insert(0, str(HERE))
elif (HERE.parent / "v0.1" / "src" / "bioreactor.py").exists():
    sys.path.insert(0, str(HERE.parent / "v0.1" / "src"))
else:
    raise SystemExit(
        "Cannot locate bioreactor.py. Place this script next to it, or run "
        "from the repo root."
    )

from bioreactor import BioreactorModel


# ---------------------------------------------------------------------
# Input-variance wrapper
# ---------------------------------------------------------------------

def run_one(env_kind: str, seed: int, ticks: int,
            sigma_input: float, swan_scale: float,
            black_swan: bool = True) -> dict:
    """
    Run a single ABM trial with explicit input variance.

    sigma_input
        Controls the spread of *starting condition variability*. This is
        the Axenie-σ axis. Concretely, we perturb:
          - initial number of yeast agents (population size)
          - initial mean defense capital
          - swan_tick (when the shock fires, if enabled)
        Each is drawn from a normal distribution with mean = nominal
        value and std = sigma_input × nominal_value (i.e., sigma_input
        is a *fractional* sigma).

    swan_scale
        Magnitude of black-swan toxin pulse. Independent of sigma_input.
    """
    # Local RNG for per-trial sampling, separate from the model's internal RNG
    local_rng = np.random.default_rng(seed * 7919 + 13)

    # Build the model with seed for reproducibility
    m = BioreactorModel(env_kind=env_kind, seed=seed, black_swan=black_swan)
    # Override swan scale
    m.env.swan_scale = swan_scale

    # Inject Axenie-σ-style variability into starting conditions.
    # The exact knobs are crude but match the spirit of "per-trial
    # input uncertainty" that the Axenie framework requires.
    if sigma_input > 0 and hasattr(m, "agents"):
        # Perturb each agent's intrinsic robustness and starting defense
        # by a small amount proportional to sigma_input.
        for a in list(m.agents):
            if hasattr(a, "intrinsic_robustness"):
                noise = 1.0 + local_rng.normal(0, sigma_input)
                a.intrinsic_robustness = max(0.01, a.intrinsic_robustness * noise)
            if hasattr(a, "defense_capital"):
                noise = 1.0 + local_rng.normal(0, sigma_input)
                a.defense_capital = max(0.0, a.defense_capital * noise)

    # Run
    df = m.run(ticks)
    final = df.iloc[-1]
    return {
        "final_biomass": float(final["biomass"]),
        "final_alive": int(final["alive"]),
        "extinct": bool(final["alive"] == 0),
        "mean_defense_at_end": float(final.get("mean_defense", np.nan)),
    }


# ---------------------------------------------------------------------
# Axenie metrics
# ---------------------------------------------------------------------

def axenie_metrics(samples: np.ndarray) -> dict:
    """Skewness, kurtosis, tail asymmetry — the antifragility signals."""
    samples = np.asarray(samples)
    return {
        "n": int(len(samples)),
        "mean": float(samples.mean()),
        "std": float(samples.std(ddof=1)),
        "median": float(np.median(samples)),
        "skewness": float(stats.skew(samples)),
        "excess_kurtosis": float(stats.kurtosis(samples)),
        "mean_minus_median": float(samples.mean() - np.median(samples)),
        "p10": float(np.percentile(samples, 10)),
        "p25": float(np.percentile(samples, 25)),
        "p50": float(np.percentile(samples, 50)),
        "p75": float(np.percentile(samples, 75)),
        "p90": float(np.percentile(samples, 90)),
        "right_tail_p90_p50": float(np.percentile(samples, 90)
                                    - np.percentile(samples, 50)),
        "left_tail_p50_p10":  float(np.percentile(samples, 50)
                                    - np.percentile(samples, 10)),
        "extinct_fraction": float((samples == 0).mean()),
    }


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=500,
                    help="trials per (schedule, sigma, swan_scale) cell")
    ap.add_argument("--ticks", type=int, default=150,
                    help="ABM ticks per trial")
    ap.add_argument("--sigmas", type=float, nargs="+",
                    default=[0.0, 0.05, 0.1, 0.2],
                    help="input variance levels (Axenie-σ axis)")
    ap.add_argument("--swan_scales", type=float, nargs="+",
                    default=[1.0, 2.5],
                    help="shock magnitudes (independent of input variance)")
    ap.add_argument("--schedules", type=str, nargs="+",
                    default=["constant", "variable"])
    ap.add_argument("--out_prefix", type=str, default="phase_a")
    ap.add_argument("--checkpoint_every", type=int, default=100,
                    help="save partial CSV every N trials per cell")
    args = ap.parse_args()

    n_cells = (len(args.sigmas) * len(args.swan_scales) * len(args.schedules))
    total_trials = n_cells * args.n
    print(f"Phase A heavy run")
    print(f"  schedules     = {args.schedules}")
    print(f"  sigmas        = {args.sigmas}")
    print(f"  swan_scales   = {args.swan_scales}")
    print(f"  N per cell    = {args.n}")
    print(f"  ticks         = {args.ticks}")
    print(f"  cells         = {n_cells}")
    print(f"  total trials  = {total_trials}")
    print()

    all_rows = []
    start = time.time()
    done = 0

    raw_path = f"{args.out_prefix}_raw.csv"
    metrics_path = f"{args.out_prefix}_metrics.csv"

    for sigma in args.sigmas:
        for swan_scale in args.swan_scales:
            for schedule in args.schedules:
                cell_start = time.time()
                cell_rows = []
                for seed in range(args.n):
                    try:
                        r = run_one(schedule, seed, args.ticks,
                                    sigma_input=sigma, swan_scale=swan_scale)
                    except Exception as e:
                        r = {"final_biomass": np.nan, "final_alive": 0,
                             "extinct": True, "mean_defense_at_end": np.nan,
                             "error": str(e)}
                    row = {
                        "schedule": schedule,
                        "sigma_input": sigma,
                        "swan_scale": swan_scale,
                        "seed": seed,
                        **r,
                    }
                    cell_rows.append(row)
                    all_rows.append(row)
                    done += 1

                    # Periodic checkpoint
                    if done % args.checkpoint_every == 0:
                        pd.DataFrame(all_rows).to_csv(raw_path, index=False)
                        elapsed = time.time() - start
                        eta = elapsed / done * (total_trials - done)
                        print(f"  [checkpoint] {done}/{total_trials} "
                              f"({100*done/total_trials:.0f}%) "
                              f"elapsed={elapsed:.0f}s  ETA={eta:.0f}s")

                cell_elapsed = time.time() - cell_start
                cell_df = pd.DataFrame(cell_rows)
                biomass = cell_df.final_biomass.dropna().values
                m = axenie_metrics(biomass) if len(biomass) > 0 else {}
                print(f"  {schedule:8s}  σ={sigma:.2f}  swan={swan_scale:.1f}  "
                      f"mean={m.get('mean', float('nan')):8.1f}  "
                      f"std={m.get('std', float('nan')):7.1f}  "
                      f"skew={m.get('skewness', float('nan')):+.2f}  "
                      f"({cell_elapsed:.0f}s)")

    # Final write
    df = pd.DataFrame(all_rows)
    df.to_csv(raw_path, index=False)

    # Per-cell metrics summary
    metrics_rows = []
    for sigma in args.sigmas:
        for swan_scale in args.swan_scales:
            for schedule in args.schedules:
                sub = df[(df.schedule == schedule)
                         & (df.sigma_input == sigma)
                         & (df.swan_scale == swan_scale)]
                biomass = sub.final_biomass.dropna().values
                if len(biomass) == 0:
                    continue
                m = axenie_metrics(biomass)
                m.update({"schedule": schedule, "sigma_input": sigma,
                          "swan_scale": swan_scale})
                metrics_rows.append(m)
    pd.DataFrame(metrics_rows).to_csv(metrics_path, index=False)

    total_elapsed = time.time() - start
    print()
    print(f"Done in {total_elapsed:.0f}s ({total_elapsed/60:.1f} min)")
    print(f"Raw     -> {os.path.abspath(raw_path)}")
    print(f"Metrics -> {os.path.abspath(metrics_path)}")
    print()
    print("Next: load metrics CSV in a notebook to inspect skewness vs sigma.")


if __name__ == "__main__":
    main()
