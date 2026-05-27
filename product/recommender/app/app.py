"""
Feed-schedule recommender — v0.2 UI.

User picks: total ticks, n_seeds, whether to include the black-swan event.
App generates ~16 candidate schedules, evaluates each with Monte Carlo,
ranks by mean yield, and shows top 5 with downside metrics.

The honesty banner is at the top, in big text, on purpose.
"""

from __future__ import annotations
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT / "product" / "recommender" / "src"))

import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from schedules import generate_all, Candidate
from recommender import (evaluate_and_compare, rank_by_yield, summary_table)
from statistics import search_inflation_warning


st.set_page_config(
    page_title="Yeast feed-schedule recommender",
    page_icon="🧪",
    layout="wide",
)


# ----------------------- header -----------------------

st.title("Yeast feed-schedule recommender")
st.markdown(
    "Compare common fed-batch feed patterns on a generic *S. cerevisiae* "
    "toy model and rank them by **predicted yield**. The output is a "
    "shortlist of schedules worth trying — not a substitute for wet-lab "
    "validation."
)

# Honesty banner: required.
st.warning(
    "⚠️ **These rankings come from a generic ABM that has not been "
    "calibrated to any specific strain.** Use them to *narrow* the search "
    "space (e.g. 'try a few pulsed schedules before exponential'), not to "
    "skip the bench. Effect sizes are illustrative, not predictive."
)


# ----------------------- sidebar -----------------------

with st.sidebar:
    st.header("Run settings")
    n_seeds = st.slider("Monte Carlo runs per candidate", 15, 80, 30, step=5,
                        help="More seeds = more reliable ranking but longer wait.")
    ticks = st.slider("Simulation length (ticks)", 80, 200, 130, step=10)
    include_swan = st.checkbox(
        "Include fat-tailed contamination shock",
        value=True,
        help="If on, also penalize schedules that crash under unexpected "
             "stress. If off, ranks by raw yield only.",
    )

    st.divider()
    st.markdown(
        "**Candidate schedules** are auto-generated from 5 patterns:\n"
        "- Constant\n- Linear ramp (up/down)\n- Exponential\n"
        "- Pulsed (bolus + starve)\n- Step-up\n\n"
        "All share the same time-averaged feed, so the comparison is about "
        "*delivery pattern*, not 'more food vs less'."
    )

    st.divider()
    expected_seconds = n_seeds * 16 * (ticks / 130) * 0.15
    st.caption(f"≈ {expected_seconds:.0f}s expected run time.")


# ----------------------- main -----------------------

run = st.button("Generate and rank schedules", type="primary",
                use_container_width=True)

if not run:
    st.info("👈 Adjust settings and click the button. With defaults, "
            "expect about a minute on a free-tier cloud instance.")
    st.stop()

# Generate candidates
candidates = generate_all(ticks=ticks)
st.markdown(f"Generated **{len(candidates)} candidate schedules**. "
            f"Evaluating each with {n_seeds} Monte Carlo runs…")

progress = st.progress(0.0, text="Starting…")

def _cb(done: int, total: int, name: str):
    progress.progress(done / total,
                      text=f"Evaluating {done}/{total}: {name}")

results, comparison = evaluate_and_compare(
    candidates, n_seeds=n_seeds, ticks=ticks,
    black_swan=include_swan, progress_cb=_cb,
)
progress.empty()

# Build a lookup from candidate name → tied_with_top boolean (since
# `ranked` reorders the results but `comparison` is indexed against
# the original `results` order).
name_to_tied = {
    results[i].candidate.name: bool(comparison.tied_with_top[i])
    for i in range(len(results))
}
name_to_ci = {
    results[i].candidate.name: (float(comparison.ci_lo[i]),
                                float(comparison.ci_hi[i]))
    for i in range(len(results))
}
ranked = rank_by_yield(results)


# ----------------------- top-5 ranking -----------------------

st.subheader("🏆 Top 5 recommended schedules")

# Statistical-honesty banner
n_tied = int(comparison.tied_with_top.sum())
n_total = len(results)
if n_tied > 1:
    st.info(
        f"📊 **Statistical note**: Of {n_total} candidates, **{n_tied} are "
        f"statistically indistinguishable** from the top performer "
        f"(Bonferroni-corrected pairwise tests + bootstrap 95% CI overlap). "
        f"Treat them as a *plausible set*, not a strict ordering."
    )
else:
    st.info(
        f"📊 **Statistical note**: The top candidate is statistically "
        f"distinct from all {n_total - 1} others — a relatively confident "
        f"recommendation. (Still requires wet-lab verification.)"
    )

st.caption("Ranked by mean final biomass across Monte Carlo runs. "
           "Statistical comparisons against #1 are shown next to each card.")

top5 = ranked[:5]
top_yield = top5[0].yield_mean if top5 else 1.0

for rank_idx, r in enumerate(top5, 1):
    pct_of_best = (r.yield_mean / top_yield * 100) if top_yield > 0 else 0
    is_tied = name_to_tied[r.candidate.name]
    ci_lo, ci_hi = name_to_ci[r.candidate.name]

    if rank_idx == 1:
        stat_label, stat_color = "👑 TOP", "#2a9d3f"
    elif is_tied:
        stat_label, stat_color = "≈ TIED", "#d49215"
    else:
        stat_label, stat_color = "× WORSE", "#b04040"

    with st.container():
        c1, c2, c3, c4 = st.columns([0.6, 2.2, 1.2, 1.2])
        with c1:
            color = "#2a9d3f" if rank_idx == 1 else "#555"
            st.markdown(
                f"<div style='font-size:2.5rem;font-weight:700;color:{color};"
                f"text-align:center'>#{rank_idx}</div>",
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(f"**{r.candidate.short_label()}**")
            st.caption(f"Pattern: `{r.candidate.pattern}` · "
                       f"internal: `{r.candidate.name}`")
            params_str = ", ".join(
                f"{k}={v}" for k, v in r.candidate.params.items()
                if not isinstance(v, list)
            )
            if params_str:
                st.caption(f"Params: {params_str}")
        with c3:
            st.metric("Yield", f"{r.yield_mean:.0f}",
                      f"95% CI: [{ci_lo:.0f}, {ci_hi:.0f}]")
        with c4:
            st.markdown(
                f"<div style='font-size:1.3rem;font-weight:700;"
                f"color:{stat_color};text-align:center;padding-top:1rem'>"
                f"{stat_label}</div>",
                unsafe_allow_html=True,
            )
            st.caption(f"Extinction: {r.extinction_rate*100:.0f}%")
        st.markdown("")


# ----------------------- search-inflation check -----------------------

st.divider()
ensemble_std = float(np.mean([r.yield_std for r in results]))
inflation = search_inflation_warning(n_trials=len(results),
                                     ensemble_std=ensemble_std)
all_means = np.array([r.yield_mean for r in results])
top_lift = ranked[0].yield_mean - all_means.mean()
real_signal_ratio = (top_lift / inflation["expected_max_under_null"]
                     if inflation["expected_max_under_null"] > 0 else float("inf"))

with st.expander("🎯 Search-inflation check (how much of '#1 winning' is just noise?)",
                 expanded=True):
    st.markdown(
        f"You evaluated **{len(results)} candidates**. Mean yield across "
        f"all = {all_means.mean():.0f}; per-candidate std = {ensemble_std:.0f}.\n\n"
        f"**Pure search noise** (if all candidates were identical) could "
        f"produce an apparent best-of-N lift of ~"
        f"**{inflation['expected_max_under_null']:.0f}** by chance alone "
        f"(extreme-value approximation, following Taleb 2024).\n\n"
        f"Your observed top-vs-mean lift is **{top_lift:.0f}**, which is "
        f"**{real_signal_ratio:.1f}× the noise estimate.**"
    )
    if real_signal_ratio < 1.5:
        st.warning(
            "⚠️ Your apparent winner is **within the search-noise envelope**. "
            "Most or all of the 'improvement' may be artifact. Treat the "
            "ranking with extreme skepticism."
        )
    elif real_signal_ratio < 3.0:
        st.info(
            "Apparent winner is above noise, but not by much. The TIED "
            "candidates above probably represent the truthful answer set."
        )
    else:
        st.success(
            "Apparent winner exceeds the noise envelope by a comfortable "
            "margin. The ranking signal is likely real (within the model)."
        )


# ----------------------- visualisation -----------------------

st.divider()
left, right = st.columns([3, 2])

with left:
    st.subheader("Yield distribution: top-5 vs constant baseline")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    # Always include constant for context, even if it isn't top-5
    plot_set = list(top5)
    constant_result = next(
        (r for r in ranked if r.candidate.pattern == "constant"), None,
    )
    if constant_result and constant_result not in plot_set:
        plot_set.append(constant_result)

    labels = [r.candidate.short_label()[:35] for r in plot_set]
    data = [r.per_seed_yields for r in plot_set]
    parts = ax.boxplot(data, vert=False, labels=labels, patch_artist=True)
    for i, patch in enumerate(parts["boxes"]):
        if i == 0:
            patch.set_facecolor("#2a9d3f")
        elif plot_set[i] is constant_result and constant_result not in top5:
            patch.set_facecolor("#b04040")
        else:
            patch.set_facecolor("#3060a0")
        patch.set_alpha(0.7)
    ax.set_xlabel("final biomass (yield proxy)")
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    st.pyplot(fig)
    st.caption(
        "Green = #1 recommendation. Blue = top-5. Red = constant baseline "
        "(shown for reference even when not in top-5). Box = IQR, whiskers "
        "= 1.5×IQR."
    )

with right:
    st.subheader("Schedule shape of #1")
    fig2, ax2 = plt.subplots(figsize=(6, 4))
    sched = top5[0].candidate.schedule
    ax2.plot(sched["tick"], sched["glucose_feed"], color="#2a9d3f", lw=2)
    ax2.fill_between(sched["tick"], 0, sched["glucose_feed"],
                     alpha=0.2, color="#2a9d3f")
    ax2.set_xlabel("tick")
    ax2.set_ylabel("glucose feed")
    ax2.set_title(top5[0].candidate.short_label())
    ax2.grid(alpha=0.2)
    fig2.tight_layout()
    st.pyplot(fig2)


# ----------------------- full table & downloads -----------------------

st.divider()
st.subheader("All candidates")
df = summary_table(ranked)
df_show = df[["label", "pattern", "yield_mean", "yield_p10",
              "yield_p90", "extinction_rate", "reliability"]].copy()
df_show.columns = [
    "Schedule", "Pattern", "Yield (mean)", "Yield (p10)",
    "Yield (p90)", "Extinction rate", "Reliability",
]
st.dataframe(
    df_show.style.format({
        "Yield (mean)": "{:.0f}",
        "Yield (p10)": "{:.0f}",
        "Yield (p90)": "{:.0f}",
        "Extinction rate": "{:.0%}",
        "Reliability": "{:.0%}",
    }),
    use_container_width=True, hide_index=True,
)

st.download_button(
    "Download full ranking (CSV)",
    df.to_csv(index=False).encode(),
    file_name="schedule_ranking.csv",
    mime="text/csv",
)

# Download the winning schedule as a CSV the user could feed back into
# the YeastFort fragility scorer.
winner_csv = top5[0].candidate.schedule.to_csv(index=False).encode()
st.download_button(
    f"Download #1 schedule (compatible with YeastFort)",
    winner_csv,
    file_name=f"recommended_{top5[0].candidate.name}.csv",
    mime="text/csv",
)


# ----------------------- footer caveats -----------------------

st.divider()
with st.expander("How to interpret these results — and what NOT to do"):
    st.markdown("""
**What this tells you (within the model's assumptions):**
- Which feed patterns the toy ABM thinks survive a fat-tailed shock better
- The trade-off between mean yield and downside risk
- An ordering useful for narrowing your wet-lab pilot from 16 schedules
  down to maybe 3 worth trying

**What this does NOT tell you:**
- The actual numerical yield you'd see in your reactor
- Whether the ranking holds for your specific strain
- Whether it holds in the presence of failure modes the model doesn't capture
  (mechanical, multi-step contamination cascades, operator error, ...)

**The right way to use it:**
1. Pick top 2–3 from the ranking.
2. Pilot them at the smallest scale your lab supports.
3. Compare measured outcomes to the model's predictions.
4. If they agree directionally, the search-space narrowing was worth it.
5. If they disagree wildly, the model is poorly calibrated to your strain
   — which is itself useful information. Feed your results back into a
   future calibration step.
""")
