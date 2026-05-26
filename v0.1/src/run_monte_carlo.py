"""
Monte Carlo experiment: run both regimes across many seeds and aggregate.
"""

from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import pandas as pd

from bioreactor import BioreactorModel


def run_one(env_kind: str, seed: int, ticks: int, black_swan: bool) -> dict:
    m = BioreactorModel(env_kind=env_kind, seed=seed, black_swan=black_swan)
    df = m.run(ticks)
    final = df.iloc[-1]
    swan_tick = m.env.swan_tick if black_swan else None
    swan_in_range = swan_tick is not None and 0 <= swan_tick < len(df)
    if swan_in_range:
        pre = df.loc[max(0, swan_tick - 1), "alive"]
        post_min_raw = df.loc[swan_tick:, "alive"].min()
        if pd.isna(post_min_raw):
            pre_int, post_int = None, None
        else:
            pre_int = int(pre)
            post_int = int(post_min_raw)
    else:
        pre_int, post_int = None, None

    return {
        "env": env_kind,
        "seed": seed,
        "final_alive": int(final["alive"]),
        "final_biomass": float(final["biomass"]),
        "mean_defense_at_end": float(final["mean_defense"]),
        "extinct": bool(final["alive"] == 0),
        "swan_tick": swan_tick if swan_in_range else None,
        "alive_pre_swan": pre_int,
        "alive_post_swan_min": post_int,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--n-seeds", type=int, default=200)
    p.add_argument("--ticks", type=int, default=200)
    p.add_argument("--no-swan", action="store_true")
    p.add_argument("--out", type=Path,
                   default=Path(__file__).parent.parent / "results")
    args = p.parse_args()
    args.out.mkdir(exist_ok=True, parents=True)

    rows = []
    for kind in ("constant", "variable"):
        for seed in range(args.n_seeds):
            rows.append(run_one(kind, seed, args.ticks,
                                black_swan=not args.no_swan))
            if (seed + 1) % 25 == 0:
                print(f"  {kind:8s} seed {seed+1}/{args.n_seeds}")

    df = pd.DataFrame(rows)
    out_csv = args.out / "monte_carlo.csv"
    df.to_csv(out_csv, index=False)
    print(f"\nWrote {out_csv}")

    summary = df.groupby("env").agg(
        n=("seed", "count"),
        extinction_rate=("extinct", "mean"),
        median_biomass=("final_biomass", "median"),
        mean_biomass=("final_biomass", "mean"),
        p10_biomass=("final_biomass", lambda x: np.percentile(x, 10)),
        p90_biomass=("final_biomass", lambda x: np.percentile(x, 90)),
        mean_defense=("mean_defense_at_end", "mean"),
    )
    print("\n=== Summary across seeds ===")
    print(summary.to_string())
    (args.out / "summary.json").write_text(summary.to_json(indent=2))


if __name__ == "__main__":
    main()
