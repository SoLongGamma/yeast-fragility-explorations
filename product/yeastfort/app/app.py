"""
YeastFort — Fragility Scorer (axis 1 MVP).

What the researcher sees:
  - Drop a CSV (or pick an example)
  - 30 seconds of computation
  - One fragility score (0-100), 3 subscores, weak-point list,
    and a single chart showing the outcome distribution.

What we actually do:
  - Run 80 Monte Carlo simulations of an ABM of S. cerevisiae under their
    protocol + a fat-tailed contamination event. The user never sees that.
"""

from __future__ import annotations
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT / "product" / "yeastfort" / "scorer"))

import io
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

from fragility import score_protocol, FragilityReport
from protocol_env import validate_protocol


# ----------------------- page config -----------------------

st.set_page_config(
    page_title="YeastFort — protocol fragility scorer",
    page_icon="🧫",
    layout="wide",
)


# ----------------------- header -----------------------

st.title("YeastFort")
st.markdown(
    "**Score your *S. cerevisiae* fermentation protocol's fragility "
    "before you run the experiment.**"
)
st.markdown(
    "Upload a protocol, get a 0–100 fragility score, three diagnostic "
    "subscores, and a list of weak points. Runs in ~20 seconds."
)

with st.expander("How does this work?", expanded=False):
    st.markdown(
        """
We simulate your protocol against 80 randomized runs that each include a
fat-tailed contamination / hardware-fault event of unknown timing and
severity. The score reflects how the population fares **across those runs**,
not just on the average one. Conceptually it answers:

> *"If I ran this protocol 80 times, how often would I get a usable result
> vs. a crash, and how similar would the usable results be to each other?"*

It is a screening tool, not a substitute for wet-lab validation. Effect
sizes are illustrative.
        """
    )


# ----------------------- sidebar: inputs -----------------------

with st.sidebar:
    st.header("Protocol input")

    example_choice = st.selectbox(
        "Try an example:",
        ("(none)", "Naive — constant T, constant feed",
         "Primed — pulsed heat + feast/famine"),
    )

    uploaded = st.file_uploader(
        "…or upload your own CSV",
        type=["csv"],
        help="Required columns: tick, temperature, pH, glucose_feed",
    )

    st.divider()
    st.markdown("**Simulation settings**")
    n_seeds = st.slider("Monte Carlo runs", 20, 200, 80, step=20)
    ticks = st.slider("Simulation length (ticks)", 60, 250, 130, step=10)

    st.divider()
    st.caption(
        "Built on the v0.1 ABM. Scores are screening estimates, not "
        "wet-lab predictions."
    )

# ----------------------- load protocol -----------------------

def load_example(name: str) -> pd.DataFrame | None:
    if name.startswith("Naive"):
        return pd.read_csv(_REPO_ROOT / "product" / "yeastfort" /
                           "examples" / "protocol_naive_constant.csv")
    if name.startswith("Primed"):
        return pd.read_csv(_REPO_ROOT / "product" / "yeastfort" /
                           "examples" / "protocol_primed_variable.csv")
    return None


protocol = None
source_label = None

if uploaded is not None:
    try:
        protocol = pd.read_csv(uploaded)
        source_label = f"uploaded: {uploaded.name}"
    except Exception as e:
        st.error(f"Could not parse the CSV: {e}")
elif example_choice != "(none)":
    protocol = load_example(example_choice)
    source_label = example_choice

if protocol is None:
    st.info("👈 Pick an example or upload a protocol CSV to get started.")
    st.markdown("**Expected CSV format:**")
    st.code(
        "tick,temperature,pH,glucose_feed\n"
        "0,30.0,5.0,5.0\n"
        "1,30.0,5.0,5.0\n"
        "...",
        language="csv",
    )
    st.stop()

ok, issues = validate_protocol(protocol)
if not ok:
    st.error("Protocol failed validation:")
    for i in issues:
        st.markdown(f"- {i}")
    st.stop()

st.success(f"Loaded protocol ({source_label}) · {len(protocol)} time points")


# ----------------------- preview the protocol -----------------------

with st.expander("Preview protocol schedule", expanded=False):
    fig_p, axes = plt.subplots(3, 1, figsize=(8, 4.5), sharex=True)
    axes[0].plot(protocol["tick"], protocol["temperature"], color="#b04040")
    axes[0].set_ylabel("temperature (°C)")
    axes[1].plot(protocol["tick"], protocol["pH"], color="#a06030")
    axes[1].set_ylabel("pH")
    axes[2].plot(protocol["tick"], protocol["glucose_feed"], color="#3060a0")
    axes[2].set_ylabel("glucose feed")
    axes[2].set_xlabel("tick")
    for a in axes:
        a.grid(alpha=0.2)
    fig_p.tight_layout()
    st.pyplot(fig_p)
    st.dataframe(protocol.head(20), use_container_width=True, hide_index=True)


# ----------------------- run the scorer -----------------------

run = st.button("Score this protocol", type="primary",
                use_container_width=True)

# Cache key: hash of the protocol contents + settings.
@st.cache_data(show_spinner=False)
def cached_score(csv_text: str, n_seeds: int, ticks: int) -> FragilityReport:
    df = pd.read_csv(io.StringIO(csv_text))
    return score_protocol(df, n_seeds=n_seeds, ticks=ticks)


if not run:
    st.stop()

progress = st.progress(0.0, text="Setting up simulations…")
status = st.empty()

def _cb(done: int, total: int):
    progress.progress(done / total,
                      text=f"Running simulation {done}/{total}…")

report = score_protocol(protocol, n_seeds=n_seeds, ticks=ticks,
                        progress_cb=_cb)
progress.empty()
status.empty()


# ----------------------- display results -----------------------

def score_color(score: float, inverted: bool = False) -> str:
    """Green/yellow/red based on score. inverted=True means lower is better
    (used for overall fragility)."""
    s = (100 - score) if inverted else score
    if s >= 70: return "#2a9d3f"
    if s >= 40: return "#d49215"
    return "#c0392b"


col1, col2, col3, col4 = st.columns(4)

with col1:
    color = score_color(report.overall_fragility, inverted=True)
    st.markdown(f"### Overall fragility")
    st.markdown(
        f"<span style='color:{color};font-size:3rem;font-weight:700'>"
        f"{report.overall_fragility:.0f}</span><span style='font-size:1.2rem'> / 100</span>",
        unsafe_allow_html=True,
    )
    st.caption("Lower is better. 0 = bulletproof, 100 = collapses on any disturbance.")

with col2:
    c = score_color(report.shock_survival)
    st.metric("Shock survival", f"{report.shock_survival:.0f}/100",
              help="Fraction of runs whose population survived the "
                   "contamination event.")

with col3:
    c = score_color(report.reproducibility)
    st.metric("Reproducibility", f"{report.reproducibility:.0f}/100",
              help="How similar the outcomes are across runs. Low = the same "
                   "protocol gives wildly different yields seed to seed.")

with col4:
    c = score_color(report.recovery)
    st.metric("Recovery", f"{report.recovery:.0f}/100",
              help="Of the runs that took a shock, how many recovered to "
                   "≥50% of the pre-shock population.")


st.divider()

left, right = st.columns([3, 2])

with left:
    st.subheader("Outcome distribution")
    fig, ax = plt.subplots(figsize=(7, 4))
    bm = report.per_seed["final_biomass"].values
    bins = np.linspace(0, max(bm.max(), 1), 30)
    ax.hist(bm, bins=bins, color="#3060a0", alpha=0.85,
            edgecolor="#1a3050")
    ax.axvline(report.final_biomass_p50, color="#b04040", lw=2,
               label=f"median = {report.final_biomass_p50:.0f}")
    ax.set_xlabel("final biomass (proxy for product titer)")
    ax.set_ylabel(f"number of runs (out of {report.n_seeds})")
    ax.set_title(f"Bimodality index: {report.bimodality_index:.2f}  "
                 f"(0 = consistent, 1 = boom-or-bust)")
    ax.legend()
    ax.grid(alpha=0.2)
    fig.tight_layout()
    st.pyplot(fig)

with right:
    st.subheader("Weak points")
    for i, w in enumerate(report.weak_points, 1):
        st.markdown(f"**{i}.** {w}")

    st.markdown(" ")
    st.markdown(f"**Yield percentiles (across {report.n_seeds} runs):**")
    st.markdown(
        f"- 10th percentile: `{report.final_biomass_p10:.0f}`\n"
        f"- median: `{report.final_biomass_p50:.0f}`\n"
        f"- 90th percentile: `{report.final_biomass_p90:.0f}`"
    )
    st.markdown(
        f"- extinction rate: `{report.extinction_rate*100:.1f}%`"
    )


# Mean trajectory
with st.expander("Population trajectory (mean + 10–90% band)", expanded=False):
    fig2, ax2 = plt.subplots(figsize=(8, 3.5))
    mt = report.mean_trajectory
    ax2.fill_between(mt["tick"], mt["alive_p10"], mt["alive_p90"],
                     color="#3060a0", alpha=0.25, label="10–90 percentile")
    ax2.plot(mt["tick"], mt["alive_mean"], color="#3060a0", lw=2,
             label="mean")
    ax2.set_xlabel("tick"); ax2.set_ylabel("alive cells")
    ax2.legend(); ax2.grid(alpha=0.2)
    fig2.tight_layout()
    st.pyplot(fig2)


# Raw data download
st.divider()
csv = report.per_seed.to_csv(index=False).encode()
st.download_button(
    "Download per-seed raw data (CSV)",
    csv,
    file_name="yeastfort_per_seed.csv",
    mime="text/csv",
)
