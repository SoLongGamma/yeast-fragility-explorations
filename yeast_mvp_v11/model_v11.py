"""
v1.1 — Robust optimization recommender (fed-batch).

Adds:
  - 6th state P (mitochondrial product, generic TCA-derived carbon)
  - Monte Carlo with 2× the realistic σ (the 'Roman training' principle)
  - p10-based ranking instead of mean-based
  - Three targets: biomass / ethanol / mitochondrial_product

Why 2× harsh:
  Real lab-to-lab CV in inoculum, μ_max, Y_XS is ~10-15%.
  We train under 20-30% to leave a safety margin for the recommendation.
  Worst-case (p10) yield is what the user actually gets in bad batches.

Why p10:
  Mean yield is what every textbook optimizes. p10 is what determines
  whether the operator's worst week is acceptable. For fed-batch
  reproducibility, p10 is the metric that matters.
"""

from __future__ import annotations
import numpy as np
from scipy.integrate import odeint


# ---------------------------------------------------------------------
# 6-state ODE — adds mitochondrial product P
# ---------------------------------------------------------------------

PARAMS = {
    "mu_max":  0.40,    # max specific growth rate [1/h]
    "Ks":      0.50,    # glucose half-saturation [g/L]
    "K_O":     0.20,    # oxygen half-saturation [% of saturation]
    "Y_XS":    0.50,    # biomass yield on glucose [g/g]
    "Y_ES":    0.45,    # ethanol yield on glucose [g/g] (when Crabtree active)
    "Y_PS":    0.20,    # mitochondrial product yield on glucose [g/g]
    "Y_XO":    1.00,    # biomass yield on oxygen [g/g]
    "m_S":     0.02,    # maintenance coefficient [g/g/h]
    "kLa":    150.0,    # mass transfer coefficient [1/h]
    "S_feed": 500.0,    # glucose concentration in feed [g/L]
    "Crabtree_threshold": 0.5,   # q_S above which Crabtree branch activates
}


def fed_batch_dynamics(state, t, feed_rate, DO_setpoint, params=PARAMS):
    """
    6-state fed-batch ODE.

    state: [X, S, E, P, DO, V]
       X  - biomass (g/L)
       S  - residual glucose (g/L)
       E  - ethanol (g/L)
       P  - mitochondrial product (g/L) — generic TCA-derived carbon
       DO - dissolved oxygen (%)
       V  - reactor volume (L)
    """
    X, S, E, P, DO, V = state
    p = params

    # Specific growth rate (Monod, glucose × oxygen)
    mu_S = p["mu_max"] * S / (p["Ks"] + S) if S > 1e-6 else 0
    mu_O = DO / (p["K_O"] + DO) if DO > 1e-6 else 0
    mu = mu_S * mu_O

    # Glucose uptake (specific)
    q_S = mu / p["Y_XS"] + p["m_S"]

    # Branch ratio: how much of the carbon goes to mitochondria vs ethanol
    # High q_S → Crabtree → ethanol branch dominates
    if q_S > p["Crabtree_threshold"]:
        f_mito = max(0, p["Crabtree_threshold"] / q_S)   # mito fraction shrinks
    else:
        f_mito = 1.0

    f_aerobic = DO / (p["K_O"] + DO) if DO > 1e-6 else 0

    # Specific rates of E and P
    q_E = (1 - f_mito) * p["Y_ES"] * q_S                  # ethanol from overflow
    q_P = f_mito * f_aerobic * p["Y_PS"] * q_S            # mito product needs O2

    # Oxygen consumption
    q_O = mu / p["Y_XO"]

    # Mass balances
    F_vol = feed_rate / p["S_feed"]
    dilution = F_vol / V if V > 1e-6 else 0

    dX = mu * X - dilution * X
    dS = -q_S * X + feed_rate - dilution * S
    dE = q_E * X - dilution * E
    dP = q_P * X - dilution * P
    dDO = p["kLa"] * (DO_setpoint - DO) - q_O * X * 1.0
    dV = F_vol

    return [dX, dS, dE, dP, dDO, dV]


def simulate(initial_state, feed_rate, DO_setpoint, duration_h=2.0,
             dt=0.1, params=PARAMS):
    """Simulate fed-batch forward."""
    t = np.arange(0, duration_h + dt, dt)
    sol = odeint(fed_batch_dynamics, initial_state, t,
                 args=(feed_rate, DO_setpoint, params))
    return t, sol


# ---------------------------------------------------------------------
# Monte Carlo with 2× harsh σ
# ---------------------------------------------------------------------

def sample_harsh_params(rng, base_params, harshness=2.0):
    """
    Sample parameters from 'harshness × realistic σ' distributions.

    realistic σ (from literature):
      mu_max: ±15%
      Y_XS:   ±10%
      X0:     ±15%
    We multiply each σ by `harshness` (default 2.0).
    """
    params = dict(base_params)
    params["mu_max"] = max(0.05, rng.normal(base_params["mu_max"],
                                            0.06 * harshness))
    params["Y_XS"]   = max(0.10, rng.normal(base_params["Y_XS"],
                                            0.05 * harshness))
    # Also perturb the inoculum (X0) — returned separately
    X0_perturb = rng.normal(1.0, 0.15 * harshness)
    return params, max(0.1, X0_perturb)


def monte_carlo_yield(initial_state, feed_rate, DO_setpoint,
                      duration_h=2.0, n_trials=100, harshness=2.0,
                      target="balanced", rng=None):
    """
    Run Monte Carlo of fed-batch and return yield distribution.

    Returns: dict with keys 'mean', 'std', 'p10', 'p50', 'p90', 'all'.
    """
    if rng is None:
        rng = np.random.default_rng(42)

    finals_X, finals_E, finals_P = [], [], []
    for _ in range(n_trials):
        params, X0_mult = sample_harsh_params(rng, PARAMS, harshness)
        # Perturb initial X
        state = list(initial_state)
        state[0] = state[0] * X0_mult

        _, sol = simulate(state, feed_rate, DO_setpoint,
                          duration_h=duration_h, params=params)
        final = sol[-1]
        finals_X.append(final[0])
        finals_E.append(final[2])
        finals_P.append(final[3])

    finals_X = np.array(finals_X)
    finals_E = np.array(finals_E)
    finals_P = np.array(finals_P)

    if target == "biomass":
        values = finals_X
    elif target == "ethanol":
        values = finals_E
    elif target == "mito" or target == "mitochondrial_product":
        values = finals_P
    else:   # balanced
        values = finals_X + finals_E + finals_P

    return {
        "mean": float(values.mean()),
        "std":  float(values.std()),
        "p10":  float(np.percentile(values, 10)),
        "p50":  float(np.percentile(values, 50)),
        "p90":  float(np.percentile(values, 90)),
        "all":  values,
        "biomass_p10": float(np.percentile(finals_X, 10)),
        "ethanol_p10": float(np.percentile(finals_E, 10)),
        "mito_p10":    float(np.percentile(finals_P, 10)),
    }


# ---------------------------------------------------------------------
# Robust recommendation
# ---------------------------------------------------------------------

def robust_recommend(initial_state, target="balanced",
                     feed_options=None, DO_options=None,
                     n_trials=100, harshness=2.0,
                     duration_h=2.0):
    """
    Grid search where each (feed, DO) is scored by *p10* under harsh σ,
    not by mean under normal σ.

    Returns: best_feed, best_DO, best_score (p10), all_results
    """
    if feed_options is None:
        feed_options = [0.0, 2.0, 4.0, 6.0, 8.0, 12.0]
    if DO_options is None:
        DO_options = [20.0, 40.0, 60.0, 80.0]

    rng = np.random.default_rng(42)
    results = []
    for f in feed_options:
        for d in DO_options:
            mc = monte_carlo_yield(initial_state, f, d,
                                   duration_h=duration_h,
                                   n_trials=n_trials,
                                   harshness=harshness,
                                   target=target, rng=rng)
            results.append({
                "feed_rate": f,
                "DO_setpoint": d,
                "p10": mc["p10"],
                "p50": mc["p50"],
                "p90": mc["p90"],
                "mean": mc["mean"],
                "std":  mc["std"],
            })

    # Rank by p10 — the worst-10% yield
    best = max(results, key=lambda r: r["p10"])
    return best["feed_rate"], best["DO_setpoint"], best["p10"], results


def explain_robust(initial_state, feed, DO, target, harshness):
    """One-line plain-language reason for the robust recommendation."""
    X, S, E, P, DO_now, V = initial_state
    parts = []
    parts.append(f"target={target}")
    parts.append(f"harshness={harshness}× realistic σ")
    parts.append(f"p10 ranked (worst 10% of batches)")

    if S < 2.0:
        parts.append(f"glucose low ({S:.1f} g/L) → feed up")
    elif S > 20.0:
        parts.append(f"glucose high → reduce feed (avoid Crabtree)")

    if target == "mito" and DO < 50.0:
        parts.append("mito target needs O2 → DO up")
    if target == "ethanol" and DO > 50.0:
        parts.append("ethanol target → micro-aerobic OK")

    return "; ".join(parts)


# ---------------------------------------------------------------------
# Quick demo when run directly
# ---------------------------------------------------------------------

if __name__ == "__main__":
    state = [2.0, 10.0, 0.5, 0.0, 50.0, 1.0]   # X, S, E, P, DO, V

    print("=" * 70)
    print("v1.1 Robust Optimization on Fed-Batch")
    print("=" * 70)
    print(f"Initial: X={state[0]}, S={state[1]}, E={state[2]}, "
          f"P={state[3]}, DO={state[4]}%, V={state[5]}L")
    print()

    for target in ["biomass", "ethanol", "mito"]:
        feed, DO, p10, results = robust_recommend(
            state, target=target, n_trials=50, harshness=2.0
        )
        print(f"Target: {target:>8s}  →  feed={feed:4.1f} g/L/hr  "
              f"DO={DO:.0f}%  p10={p10:6.2f} g/L")
        # Show top 3 alternatives
        sorted_r = sorted(results, key=lambda r: -r["p10"])
        for r in sorted_r[:3]:
            print(f"     alt: feed={r['feed_rate']:4.1f} DO={r['DO_setpoint']:.0f}% "
                  f"p10={r['p10']:5.2f}  mean={r['mean']:5.2f}  "
                  f"std={r['std']:4.2f}")
        print()
