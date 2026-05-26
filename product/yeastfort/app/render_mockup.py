"""Render a static dashboard mockup for use in slides/README."""

from __future__ import annotations
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "scorer"))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import Rectangle

from fragility import score_protocol

OUT = _HERE.parent / "examples" / "dashboard_mockup.png"


def score(name: str) -> dict:
    df = pd.read_csv(_HERE.parent / "examples" /
                     f"protocol_{name}.csv")
    r = score_protocol(df, n_seeds=60, ticks=130)
    return {"name": name, "report": r, "protocol": df}


def color_for(score: float, inverted: bool = False) -> str:
    s = (100 - score) if inverted else score
    if s >= 70: return "#2a9d3f"
    if s >= 40: return "#d49215"
    return "#c0392b"


def render(reports: list[dict], out: Path):
    fig = plt.figure(figsize=(15, 9))
    gs = gridspec.GridSpec(2, 1, figure=fig, hspace=0.42)

    for row_idx, item in enumerate(reports):
        name, r, proto = item["name"], item["report"], item["protocol"]
        row_gs = gridspec.GridSpecFromSubplotSpec(
            1, 5, subplot_spec=gs[row_idx],
            width_ratios=[1.4, 0.9, 0.9, 0.9, 2.0], wspace=0.45,
        )

        # Title row
        title = "Naive protocol — constant T / constant feed" \
            if "naive" in name else \
            "Primed protocol — pulsed heat shock + feast/famine"
        fig.text(0.02, 0.96 - 0.50 * row_idx, title,
                 fontsize=13, fontweight="bold")

        # Big overall score
        ax = fig.add_subplot(row_gs[0])
        ax.axis("off")
        c = color_for(r.overall_fragility, inverted=True)
        ax.text(0.5, 0.78, f"{r.overall_fragility:.0f}", ha="center",
                fontsize=60, fontweight="bold", color=c)
        ax.text(0.5, 0.32, "/ 100  overall fragility", ha="center",
                fontsize=11, color="#444")
        ax.text(0.5, 0.10, "(lower is better)", ha="center",
                fontsize=9, color="#777", style="italic")

        # Three subscore cards
        for k, (label, val) in enumerate([
            ("Shock\nsurvival", r.shock_survival),
            ("Reproduci-\nbility", r.reproducibility),
            ("Recovery", r.recovery),
        ]):
            ax = fig.add_subplot(row_gs[1 + k])
            ax.axis("off")
            cc = color_for(val)
            ax.add_patch(Rectangle((0.05, 0.10), 0.90, 0.80, facecolor="white",
                                   edgecolor=cc, lw=2.2))
            ax.text(0.5, 0.65, f"{val:.0f}", ha="center", fontsize=32,
                    fontweight="bold", color=cc)
            ax.text(0.5, 0.30, label, ha="center", fontsize=10,
                    color="#333")

        # Histogram
        ax = fig.add_subplot(row_gs[4])
        bm = r.per_seed["final_biomass"].values
        bins = np.linspace(0, max(bm.max(), 1), 25)
        ax.hist(bm, bins=bins, color="#3060a0", alpha=0.85,
                edgecolor="#1a3050")
        ax.set_title(f"Outcome distribution — bimodality index "
                     f"{r.bimodality_index:.2f}", fontsize=10)
        ax.set_xlabel("final biomass", fontsize=9)
        ax.set_ylabel(f"runs out of {r.n_seeds}", fontsize=9)
        ax.tick_params(labelsize=8)

    fig.suptitle("YeastFort — protocol fragility scorer",
                 fontsize=15, fontweight="bold", y=0.995)
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out}")


if __name__ == "__main__":
    reports = [score("naive_constant"), score("primed_variable")]
    render(reports, OUT)
