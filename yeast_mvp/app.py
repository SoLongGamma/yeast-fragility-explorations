"""
Yeast Fed-Batch MVP — single-screen Streamlit app.

User enters current measurements. App recommends next-hour feed rate
and DO setpoint. That's it.

No data is sent anywhere. All calculations are local. Source code is open.
"""

import streamlit as st
import numpy as np
import pandas as pd
from model import recommend, simulate, explain, PARAMS


st.set_page_config(page_title="Yeast Fed-Batch MVP", layout="wide")

st.title("Yeast Fed-Batch — Feed & DO Recommendation")
st.caption(
    "Enter your current bioreactor measurements. The app suggests a feed "
    "rate and DO setpoint for the next hour, based on a 5-state ODE model "
    "of *S. cerevisiae* on glucose. Literature-average parameters. "
    "**Research/exploratory tool — not for GMP use. Your data never leaves "
    "this browser.**"
)

col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("Current state")

    X = st.number_input("Biomass X (g/L)", min_value=0.0, max_value=200.0,
                        value=3.0, step=0.5)
    S = st.number_input("Residual glucose S (g/L)", min_value=0.0,
                        max_value=200.0, value=5.0, step=0.5)
    E = st.number_input("Ethanol E (g/L)", min_value=0.0, max_value=200.0,
                        value=1.0, step=0.5)
    DO = st.number_input("Dissolved oxygen DO (%)", min_value=0.0,
                         max_value=100.0, value=50.0, step=5.0)
    V = st.number_input("Reactor volume V (L)", min_value=0.1,
                        max_value=10000.0, value=1.0, step=0.1)

    st.subheader("Objective")
    objective = st.radio(
        "Optimize for:",
        ["balanced", "biomass", "ethanol"],
        horizontal=True,
        help=(
            "biomass: aerobic, anti-Crabtree; "
            "ethanol: micro-aerobic, fermentation; "
            "balanced: both."
        ),
    )

    run_button = st.button("Recommend", type="primary")

with col_right:
    if run_button:
        state = [X, S, E, DO, V]
        feed, do_setpoint, score, all_results = recommend(state, objective)

        st.subheader("Recommendation (next 1 hour)")

        m1, m2 = st.columns(2)
        m1.metric("Feed rate", f"{feed:.1f} g/L/hr")
        m2.metric("DO setpoint", f"{do_setpoint:.0f}%")

        st.markdown(f"**Reasoning:** {explain(state, feed, do_setpoint)}")

        # Show expected trajectory for next 2h with chosen recommendation
        st.subheader("Expected trajectory (2 h)")
        t, sol = simulate(state, feed, do_setpoint, duration_h=2.0)
        df = pd.DataFrame(
            {"hour": t, "biomass (g/L)": sol[:, 0],
             "glucose (g/L)": sol[:, 1], "ethanol (g/L)": sol[:, 2],
             "DO (%)": sol[:, 3]}
        ).set_index("hour")
        st.line_chart(df)

        # Show the full grid for transparency
        with st.expander("Show all (feed, DO) combinations evaluated"):
            grid = pd.DataFrame(all_results)
            grid_pivot = grid.pivot(index="feed_rate", columns="DO_setpoint",
                                    values="score")
            st.dataframe(grid_pivot.style.format("{:.2f}").background_gradient(
                cmap="viridis"))
            st.caption("Higher = better. The recommendation is the cell with "
                       "the highest value.")
    else:
        st.info("Enter your current state on the left and click "
                "**Recommend**.")

# Footer — transparency
st.divider()
st.caption(
    f"Model: 5-state Monod ODE (X, S, E, DO, V). "
    f"Literature-average S. cerevisiae parameters: "
    f"μ_max={PARAMS['mu_max']}, Ks={PARAMS['Ks']} g/L, "
    f"Y_XS={PARAMS['Y_XS']}, Crabtree threshold "
    f"q_S>{PARAMS['Crabtree_threshold']}. "
    f"Source code: https://github.com/SoLongGamma/yeast-fragility-explorations"
)
