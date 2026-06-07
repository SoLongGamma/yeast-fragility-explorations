"""
5-state ODE model for yeast fed-batch fermentation.

States: X (biomass), S (substrate/glucose), E (ethanol), DO (oxygen), V (volume).
Inputs: feed rate F (g/L/hr glucose), DO setpoint (%).

Parameters are literature averages for S. cerevisiae on glucose.
Not strain-specific. This is for MVP only — a starting point for the user.
"""

import numpy as np
from scipy.integrate import odeint


# Literature-average parameters (S. cerevisiae, glucose, aerobic)
PARAMS = {
    "mu_max":  0.40,    # max specific growth rate [1/h]
    "Ks":      0.50,    # glucose half-saturation [g/L]
    "K_O":     0.20,    # oxygen half-saturation [% of saturation]
    "Y_XS":    0.50,    # biomass yield on glucose [g/g]
    "Y_ES":    0.45,    # ethanol yield on glucose [g/g] (Crabtree zone)
    "Y_XO":    1.00,    # biomass yield on oxygen [g/g]
    "m_S":     0.02,    # maintenance coefficient [g/g/h]
    "kLa":    150.0,    # mass transfer coefficient [1/h, typical 5L]
    "S_feed": 500.0,    # glucose concentration in feed [g/L]
    "DO_sat": 100.0,    # DO at saturation [%]
    "Crabtree_threshold": 5.0,   # glucose uptake above which ethanol forms
}


def fermentation_dynamics(state, t, feed_rate, DO_setpoint, params=PARAMS):
    """
    ODE right-hand side for 5-state fed-batch fermentation.

    state: [X, S, E, DO, V] in [g/L, g/L, g/L, %, L]
    feed_rate: F in g/L/hr (substrate added to reactor)
    DO_setpoint: target DO in % (controller maintains via aeration)
    """
    X, S, E, DO, V = state
    p = params

    # Specific growth rate (Monod, dual-substrate: glucose + oxygen)
    mu_S = p["mu_max"] * S / (p["Ks"] + S) if S > 1e-6 else 0
    mu_O = DO / (p["K_O"] + DO) if DO > 1e-6 else 0
    mu = mu_S * mu_O

    # Glucose uptake rate (specific)
    q_S = mu / p["Y_XS"] + p["m_S"]

    # Crabtree: if glucose uptake exceeds threshold, ethanol forms
    if q_S > p["Crabtree_threshold"]:
        q_E = p["Y_ES"] * (q_S - p["Crabtree_threshold"])
    else:
        q_E = 0

    # Oxygen consumption
    q_O = mu / p["Y_XO"]

    # Mass balances
    F_vol = feed_rate / p["S_feed"]   # feed flow rate [L/hr]
    dilution = F_vol / V if V > 1e-6 else 0

    dX = mu * X - dilution * X
    dS = -q_S * X + feed_rate - dilution * S
    dE = q_E * X - dilution * E
    # DO dynamics: controller drives toward setpoint, microbes consume
    dDO = p["kLa"] * (DO_setpoint - DO) - q_O * X * 1.0   # 1.0 = unit conv
    dV = F_vol

    return [dX, dS, dE, dDO, dV]


def simulate(initial_state, feed_rate, DO_setpoint, duration_h=1.0,
             dt=0.1, params=PARAMS):
    """Simulate the system forward for `duration_h` hours with given inputs."""
    t = np.arange(0, duration_h + dt, dt)
    sol = odeint(fermentation_dynamics, initial_state, t,
                 args=(feed_rate, DO_setpoint, params))
    return t, sol


def evaluate_setpoint(initial_state, feed_rate, DO_setpoint,
                      objective="balanced", horizon_h=2.0):
    """
    Evaluate one (feed, DO) choice by simulating forward.

    Returns a single score; higher is better.
    objective: "biomass", "ethanol", or "balanced"
    """
    _, sol = simulate(initial_state, feed_rate, DO_setpoint, duration_h=horizon_h)
    final = sol[-1]
    X_final, S_final, E_final, DO_final, V_final = final

    # Penalize states going negative (numerical noise) or out of bounds
    if X_final < 0 or DO_final < 0 or S_final < 0:
        return -1e6

    if objective == "biomass":
        return X_final
    elif objective == "ethanol":
        return E_final
    else:   # balanced
        # Normalize roughly: biomass ~10s of g/L, ethanol ~10s of g/L
        return X_final + E_final


def recommend(initial_state, objective="balanced",
              feed_options=None, DO_options=None):
    """
    Grid search over (feed_rate, DO_setpoint) to find best combination.

    Returns:
        best_feed, best_DO, best_score, all_results
    """
    if feed_options is None:
        feed_options = [0.0, 2.0, 4.0, 6.0, 8.0, 12.0]   # g/L/hr
    if DO_options is None:
        DO_options = [20.0, 40.0, 60.0, 80.0]              # %

    results = []
    for f in feed_options:
        for d in DO_options:
            score = evaluate_setpoint(initial_state, f, d, objective)
            results.append({"feed_rate": f, "DO_setpoint": d, "score": score})

    best = max(results, key=lambda r: r["score"])
    return best["feed_rate"], best["DO_setpoint"], best["score"], results


def explain(initial_state, recommendation_feed, recommendation_DO):
    """One-line plain-language reason for the recommendation."""
    X, S, E, DO, V = initial_state
    reasons = []
    if S < 2.0:
        reasons.append(f"glucose low ({S:.1f} g/L) → feed up")
    elif S > 20.0:
        reasons.append(f"glucose high ({S:.1f} g/L) → reduce feed (avoid Crabtree)")
    else:
        reasons.append(f"glucose mid-range ({S:.1f} g/L) → moderate feed")

    if DO < 30.0:
        reasons.append(f"DO low ({DO:.0f}%) → DO setpoint up")
    elif DO > 70.0:
        reasons.append(f"DO high ({DO:.0f}%) → DO setpoint can drop")
    else:
        reasons.append(f"DO mid-range ({DO:.0f}%) → maintain")

    return "; ".join(reasons)


if __name__ == "__main__":
    # Quick test
    state = [2.0, 10.0, 0.5, 50.0, 1.0]   # X=2, S=10, E=0.5, DO=50%, V=1L
    feed, DO, score, all_results = recommend(state, objective="balanced")
    print(f"Initial state: X={state[0]}, S={state[1]}, E={state[2]}, "
          f"DO={state[3]}%, V={state[4]}L")
    print(f"Recommendation: feed_rate = {feed} g/L/hr, DO setpoint = {DO}%")
    print(f"Expected score (X+E): {score:.2f}")
    print(f"Reason: {explain(state, feed, DO)}")
