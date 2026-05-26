"""
P0-2: Swan timing sweep.

Question: does variable regime *always* win, or only when swan fires
after defense buildup has had time to happen?

If variable wins at every swan_tick — the model is trivially rigged.
If variable loses at early swan_tick — the model is at least directionally
honest (defense takes time to build, and you can't have advantage from
something you haven't built).

We fix swan_tick at a grid of values rather than letting it draw randomly.
"""

from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from bioreactor import BioreactorModel
from environment import make_environment


def run_with_fixed_swan(env_kind: str, seed: int, ticks: int,
                        swan_tick: int) -> dict:
    """Run one simulation with the swan firing at a SPECIFIC tick."""
    m = BioreactorModel(env_kind=env_kind, seed=seed, black_swan=True)
    # Override the randomly-chosen swan_tick with our fixed value.
    m.env.swan_tick = swan_tick
    df = m.run(ticks)
    final = df.iloc[-1]
    return {
        "env": env_kind,
        "seed": seed,
        "swan_tick": swan_tick,
        "final_alive": int(final["alive"]),
        "final_biomass": float(final["biomass"]),
        "mean_defense_at_swan": float(
            df.loc[swan_tick - 1, "mean_defense"] if swan_tick > 0 else 0.0
        ),
        "extinct": bool(final["alive"] == 0),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--n-seeds", type=int, default=100,
                   help="seeds per (regime × swan_tick) cell")
    p.add_argument("--ticks", type=int, default=150)
    p.add_argument("--swan-ticks", type=int, nargs="+",
                   default=[5, 15, 25, 35, 50, 75, 100, 125])
    p.add_argument("--out", type=Path,
                   default=Path(__file__).parent.parent / "results")
    args = p.parse_args()
    args.out.mkdir(exist_ok=True, parents=True)

    rows = []
    total = len(args.swan_ticks) * 2 * args.n_seeds
    done = 0
    for swan_t in args.swan_ticks:
        for kind in ("constant", "variable"):
            for seed in range(args.n_seeds):
                rows.append(run_with_fixed_swan(kind, seed, args.ticks, swan_t))
                done += 1
            print(f"  swan_tick={swan_t:3d} {kind:8s} done "
                  f"({done}/{total})")

    df = pd.DataFrame(rows)
    out_csv = args.out / "swan_timing_sweep.csv"
    df.to_csv(out_csv, index=False)
    print(f"\nWrote {out_csv}")

    # Headline summary
    summary = df.groupby(["swan_tick", "env"]).agg(
        n=("seed", "count"),
        extinction_rate=("extinct", "mean"),
        median_biomass=("final_biomass", "median"),
        mean_defense_at_swan=("mean_defense_at_swan", "mean"),
    ).reset_index()
    print("\n=== Extinction rate vs swan timing ===")
    pivot = summary.pivot(index="swan_tick", columns="env",
                          values="extinction_rate")
    pivot["advantage_pp"] = (pivot["constant"] - pivot["variable"]) * 100
    print(pivot.round(3).to_string())

    # ---- Figure ----
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.3))

    # Panel A: extinction rate by swan timing
    ax = axes[0]
    for kind, color in (("constant", "#b04040"), ("variable", "#3060a0")):
        sub = summary[summary.env == kind].sort_values("swan_tick")
        ax.plot(sub.swan_tick, sub.extinction_rate, "o-",
                color=color, lw=2, ms=7, label=kind)
    ax.set_xlabel("swan_tick (when contamination fires)")
    ax.set_ylabel("extinction rate")
    ax.set_ylim(-0.05, 1.05)
    ax.set_title("Extinction rate vs. timing of the black swan")
    ax.axhline(0.5, color="gray", lw=0.5, ls=":")
    ax.legend()

    # Panel B: defense capital that variable HAS BUILT by swan_tick
    ax = axes[1]
    var_sub = summary[summary.env == "variable"].sort_values("swan_tick")
    ax.plot(var_sub.swan_tick, var_sub.mean_defense_at_swan, "o-",
            color="#3060a0", lw=2, ms=7, label="variable")
    con_sub = summary[summary.env == "constant"].sort_values("swan_tick")
    ax.plot(con_sub.swan_tick, con_sub.mean_defense_at_swan, "o-",
            color="#b04040", lw=2, ms=7, label="constant")
    ax.set_xlabel("swan_tick")
    ax.set_ylabel("mean defense capital at swan moment")
    ax.set_title("Defense capital the population has built up\nby the time the swan fires")
    ax.legend()

    fig.suptitle("P0-2: does variable regime win at every swan timing, "
                 "or only when it has had time to prime?", fontsize=11)
    fig.tight_layout()
    out_fig = args.out / "p0_swan_timing_sweep.png"
    fig.savefig(out_fig, dpi=130)
    plt.close(fig)
    print(f"Wrote {out_fig}")


if __name__ == "__main__":
    main()
