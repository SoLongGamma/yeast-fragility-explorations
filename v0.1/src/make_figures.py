"""
Plots for v0.1:
  fig1_population_trajectories.png  — alive over time, both regimes, many seeds
  fig2_outcome_distribution.png     — distribution of final biomass (Jensen)
  fig3_extinction_bars.png          — extinction rates
  fig4_defense_buildup.png          — mean defense capital over time
"""

from __future__ import annotations
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

from bioreactor import BioreactorModel


RESULTS = Path(__file__).parent.parent / "results"
RESULTS.mkdir(exist_ok=True, parents=True)


def collect_trajectories(env_kind: str, n_seeds: int, ticks: int):
    rows = []
    for s in range(n_seeds):
        m = BioreactorModel(env_kind=env_kind, seed=s)
        df = m.run(ticks)
        df = df.assign(seed=s, env=env_kind, tick=range(len(df)))
        rows.append(df)
    return pd.concat(rows, ignore_index=True)


def fig1_trajectories(ticks: int = 150, n_seeds: int = 60):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    for ax, kind, color in zip(
        axes, ("constant", "variable"), ("#b04040", "#3060a0")
    ):
        traj = collect_trajectories(kind, n_seeds, ticks)
        for s in range(n_seeds):
            sub = traj[traj.seed == s]
            ax.plot(sub.tick, sub.alive, color=color, alpha=0.10, lw=0.8)
        median = traj.groupby("tick").alive.median()
        ax.plot(median.index, median.values, color=color, lw=2.2,
                label="median")
        ax.set_title(f"{kind} environment ({n_seeds} seeds)")
        ax.set_xlabel("tick"); ax.set_ylabel("alive cells")
        ax.legend(loc="upper left")
    fig.suptitle("Population over time, each line = one Monte Carlo seed",
                 fontsize=11)
    fig.tight_layout()
    out = RESULTS / "fig1_population_trajectories.png"
    fig.savefig(out, dpi=130); plt.close(fig)
    print(f"  -> {out}")


def fig2_outcome_distribution():
    df = pd.read_csv(RESULTS / "monte_carlo.csv")
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    bins = np.linspace(0, max(df.final_biomass.max(), 1), 40)
    for kind, color in (("constant", "#b04040"), ("variable", "#3060a0")):
        sub = df[df.env == kind].final_biomass
        ax.hist(sub, bins=bins, alpha=0.55, color=color,
                label=f"{kind} (median={sub.median():.0f}, mean={sub.mean():.0f})")
    ax.set_xlabel("final biomass (proxy for product titer)")
    ax.set_ylabel("count of Monte Carlo runs")
    ax.set_title("Outcome distribution under a fat-tailed contamination shock\n"
                 "Same mean environment — only the variance differs")
    ax.legend()
    fig.tight_layout()
    out = RESULTS / "fig2_outcome_distribution.png"
    fig.savefig(out, dpi=130); plt.close(fig)
    print(f"  -> {out}")


def fig3_extinction_bars():
    df = pd.read_csv(RESULTS / "monte_carlo.csv")
    rates = df.groupby("env").extinct.mean()
    fig, ax = plt.subplots(figsize=(5.5, 4))
    colors = ["#b04040", "#3060a0"]
    bars = ax.bar(rates.index, rates.values, color=colors, width=0.55)
    for b, v in zip(bars, rates.values):
        ax.text(b.get_x() + b.get_width()/2, v + 0.01, f"{v*100:.1f}%",
                ha="center", fontsize=11)
    ax.set_ylim(0, 1.05); ax.set_ylabel("extinction rate")
    ax.set_title("Total ruin probability — black-swan survival")
    fig.tight_layout()
    out = RESULTS / "fig3_extinction_bars.png"
    fig.savefig(out, dpi=130); plt.close(fig)
    print(f"  -> {out}")


def fig4_defense_buildup(ticks: int = 150, n_seeds: int = 40):
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    for kind, color in (("constant", "#b04040"), ("variable", "#3060a0")):
        traj = collect_trajectories(kind, n_seeds, ticks)
        m = traj.groupby("tick").mean_defense.mean()
        q1 = traj.groupby("tick").mean_defense.quantile(0.25)
        q3 = traj.groupby("tick").mean_defense.quantile(0.75)
        ax.plot(m.index, m.values, color=color, lw=2, label=kind)
        ax.fill_between(m.index, q1.values, q3.values, color=color, alpha=0.2)
    ax.set_xlabel("tick"); ax.set_ylabel("mean defense capital (population)")
    ax.set_title("Hormetic priming over time\n"
                 "(HSPs / trehalose / antioxidants proxy, IQR shaded)")
    ax.legend()
    fig.tight_layout()
    out = RESULTS / "fig4_defense_buildup.png"
    fig.savefig(out, dpi=130); plt.close(fig)
    print(f"  -> {out}")


if __name__ == "__main__":
    print("Rendering figures...")
    fig2_outcome_distribution()
    fig3_extinction_bars()
    fig1_trajectories()
    fig4_defense_buildup()
    print("Done.")
