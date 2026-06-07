"""
Yeast Fed-Batch v1.1 — Robust Optimization Streamlit App.

Difference from v1.0:
  - 6 states (adds mitochondrial product P)
  - Monte Carlo with user-controlled harshness (1× to 3×)
  - Recommendations ranked by p10, not mean
  - Distribution histograms shown for each recommendation
  - Explicit "worst-case 10%" guarantee in the UI

No data leaves the browser. Open source.
"""

import streamlit as st
import numpy as np
import pandas as pd
from model_v11 import (
    PARAMS, simulate, robust_recommend, monte_carlo_yield, explain_robust
)


st.set_page_config(page_title="Yeast Fed-Batch v1.1 (Robust)", layout="wide")

st.title("Yeast Fed-Batch — Robust Recommendation (v1.1)")
st.caption(
    "Recommendations are ranked by **p10** (worst-10% yield), not by "
    "mean. Monte Carlo runs at **2× the realistic σ** by default — the "
    "'train hard, deploy normal' principle. **Research/exploratory tool. "
    "Your data stays in this browser.**"
)

col_left, col_right = st.columns([1, 1.2])

with col_left:
    st.subheader("Current state (fed-batch)")
    X = st.number_input("Biomass X (g/L)", 0.0, 200.0, 3.0, 0.5)
    S = st.number_input("Residual glucose S (g/L)", 0.0, 200.0, 5.0, 0.5)
    E = st.number_input("Ethanol E (g/L)", 0.0, 200.0, 1.0, 0.5)
    P = st.number_input("Mitochondrial product P (g/L)", 0.0, 100.0, 0.0, 0.5,
                        help="Generic TCA-derived carbon (citrate/succinate/etc.)")
    DO = st.number_input("Dissolved oxygen DO (%)", 0.0, 100.0, 50.0, 5.0)
    V = st.number_input("Reactor volume V (L)", 0.1, 10000.0, 1.0, 0.1)

    st.subheader("Target")
    target = st.radio(
        "Optimize for:",
        ["biomass", "ethanol", "mito"],
        horizontal=True,
        help=(
            "mito = mitochondrial TCA-derived product (citrate, "
            "succinate, malate, etc.). Aerobic, Crabtree-avoiding."
        ),
    )

    st.subheader("Robustness settings")
    harshness = st.slider(
        "Training harshness (× realistic σ)",
        min_value=1.0, max_value=3.0, value=2.0, step=0.25,
        help=(
            "1× = train at realistic noise. 2× = train at 2× harsher "
            "than real (recommended). 3× = very conservative."
        ),
    )
    n_trials = st.select_slider(
        "Monte Carlo samples per (feed, DO) combination",
        options=[50, 100, 200, 500], value=100,
        help="More samples = more stable p10 estimate, but slower."
    )
    horizon = st.slider("Horizon (hours)", 1.0, 12.0, 4.0, 0.5)

    run_button = st.button("Recommend (robust)", type="primary")

with col_right:
    if run_button:
        state = [X, S, E, P, DO, V]
        with st.spinner(f"Running Monte Carlo (24 combinations × "
                        f"{n_trials} trials)..."):
            feed, do_setpoint, p10, results = robust_recommend(
                state, target=target, n_trials=n_trials,
                harshness=harshness, duration_h=horizon,
            )

        st.subheader("Robust recommendation (next " f"{horizon:.1f} h)")
        m1, m2, m3 = st.columns(3)
        m1.metric("Feed rate", f"{feed:.1f} g/L/hr")
        m2.metric("DO setpoint", f"{do_setpoint:.0f}%")
        m3.metric(f"p10 yield ({target})", f"{p10:.2f} g/L",
                  help="Worst-case 10% — 90% of batches do at least this well")

        st.markdown(
            f"**Reasoning:** {explain_robust(state, feed, do_setpoint, target, harshness)}"
        )

        # Distribution of the recommended setpoint
        st.subheader(f"Yield distribution under recommendation (N={n_trials})")
        rng = np.random.default_rng(42)
        dist = monte_carlo_yield(state, feed, do_setpoint,
                                 duration_h=horizon, n_trials=n_trials,
                                 harshness=harshness, target=target, rng=rng)

        col_a, col_b = st.columns([2, 1])
        with col_a:
            # Build histogram with numeric bin centers (Streamlit-safe).
            # pd.cut produces interval labels like "(0.6, 0.8]" which
            # Streamlit/altair cannot serialize — use numeric centers.
            counts, edges = np.histogram(dist["all"], bins=20)
            centers = (edges[:-1] + edges[1:]) / 2
            hist_df = pd.DataFrame({"count": counts},
                                   index=np.round(centers, 2))
            hist_df.index.name = "yield (g/L)"
            st.bar_chart(hist_df)
        with col_b:
            st.markdown(
                f"- **mean** = {dist['mean']:.2f}\n"
                f"- **std** = {dist['std']:.2f}\n"
                f"- **p10** = {dist['p10']:.2f}  ← *recommendation criterion*\n"
                f"- **p50** = {dist['p50']:.2f}\n"
                f"- **p90** = {dist['p90']:.2f}\n"
            )

        # Top 5 alternatives sorted by p10
        st.subheader("Top 5 (feed, DO) combinations by p10")
        df = pd.DataFrame(results).sort_values("p10", ascending=False).head(5)
        df = df[["feed_rate", "DO_setpoint", "p10", "p50", "p90", "mean", "std"]]
        st.dataframe(df.style.format("{:.2f}"))

        # Trajectory under recommendation (single sample, mean parameters)
        st.subheader(f"Expected trajectory under recommendation ({horizon:.1f}h)")
        t, sol = simulate(state, feed, do_setpoint, duration_h=horizon)
        traj = pd.DataFrame({
            "hour":     t,
            "X (g/L)":  sol[:, 0],
            "S (g/L)":  sol[:, 1],
            "E (g/L)":  sol[:, 2],
            "P (g/L)":  sol[:, 3],
            "DO (%)":   sol[:, 4],
        }).set_index("hour")
        st.line_chart(traj)

    else:
        st.info("Enter your current state on the left and click "
                "**Recommend (robust)**.\n\n"
                "v1.1 differences from v1.0:\n"
                "- Adds *mitochondrial product P* as a 6th state\n"
                "- Monte Carlo under 2× harsh σ\n"
                "- Ranks by p10 (worst-case 10%), not mean\n"
                "- Shows full yield distribution, not just a point\n"
                "- 'Roman training' principle: train hard, deploy under "
                "real conditions")

st.divider()
st.caption(
    f"Model: 6-state fed-batch ODE (X, S, E, P, DO, V). "
    f"Literature-average S. cerevisiae parameters. "
    f"Mito product = generic TCA-derived carbon. "
    f"Source: github.com/SoLongGamma/yeast-fragility-explorations"
)
