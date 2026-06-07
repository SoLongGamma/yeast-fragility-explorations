"""
Yeast Fed-Batch RISK MAP — 'avoid the bad region' tool.

Philosophy difference from v1.1:
  v1.1 said "here's the BEST (feed, DO)".
  This says "here are the DANGEROUS (feed, DO) — avoid them; pick freely
  among the safe ones."

This is easier and safer: identifying bad regions tolerates a rough
model, whereas pinpointing the optimum needs an accurate one.

Lab-specific: each lab enters a few past batches → parameter
distribution is estimated → Monte Carlo uses THAT lab's distribution
→ the risk map is specific to that lab.

Monte Carlo role: for each (feed, DO) cell, run N trials sampling from
the lab's parameter distribution. Classify the cell by failure rate
and p10, not by mean.
"""

from __future__ import annotations
import numpy as np
from scipy.integrate import odeint


PARAMS = {
    "mu_max": 0.40, "Ks": 0.50, "K_O": 0.20, "Y_XS": 0.50,
    "Y_ES": 0.45, "Y_PS": 0.20, "Y_XO": 1.00, "m_S": 0.02,
    "kLa": 150.0, "S_feed": 500.0, "Crabtree_threshold": 0.5,
}


def dynamics(state, t, feed, DO_sp, p):
    X, S, E, P, DO, V = state
    mu_S = p["mu_max"] * S / (p["Ks"] + S) if S > 1e-6 else 0
    mu_O = DO / (p["K_O"] + DO) if DO > 1e-6 else 0
    mu = mu_S * mu_O
    q_S = mu / p["Y_XS"] + p["m_S"]
    f_mito = max(0, p["Crabtree_threshold"] / q_S) if q_S > p["Crabtree_threshold"] else 1.0
    f_aer = DO / (p["K_O"] + DO) if DO > 1e-6 else 0
    q_E = (1 - f_mito) * p["Y_ES"] * q_S
    q_P = f_mito * f_aer * p["Y_PS"] * q_S
    q_O = mu / p["Y_XO"]
    F_vol = feed / p["S_feed"]
    dil = F_vol / V if V > 1e-6 else 0
    return [mu*X - dil*X, -q_S*X + feed - dil*S, q_E*X - dil*E,
            q_P*X - dil*P, p["kLa"]*(DO_sp - DO) - q_O*X, F_vol]


def simulate(state0, feed, DO_sp, dur=8.0, dt=0.2, p=PARAMS):
    t = np.arange(0, dur+dt, dt)
    sol = odeint(dynamics, state0, t, args=(feed, DO_sp, p))
    return t, sol


def estimate_lab_params(past_batches):
    """
    Estimate this lab's parameter distribution from a few past batches.

    past_batches: list of dicts, each with at least 'mu_max_obs'
                  (or we infer from X0, X_final, duration).
    Returns (mean_params, sigma_dict) for Monte Carlo sampling.

    For MVP: just compute mean and std of mu_max from observations.
    If only 1-2 batches, fall back to literature σ.
    """
    if not past_batches:
        return PARAMS, {"mu_max": 0.06, "Y_XS": 0.05, "X0": 0.15}

    mu_obs = [b["mu_max_obs"] for b in past_batches if "mu_max_obs" in b]
    if len(mu_obs) >= 2:
        mu_mean = float(np.mean(mu_obs))
        mu_std  = float(np.std(mu_obs, ddof=1))
    elif len(mu_obs) == 1:
        mu_mean = mu_obs[0]
        mu_std  = 0.06   # fall back to literature
    else:
        mu_mean, mu_std = PARAMS["mu_max"], 0.06

    params = dict(PARAMS)
    params["mu_max"] = mu_mean
    sigma = {"mu_max": mu_std, "Y_XS": 0.05, "X0": 0.15}
    return params, sigma


def classify_cell(state0, feed, DO_sp, lab_params, lab_sigma,
                  n_trials=60, dur=8.0, harshness=1.5, rng=None):
    """
    Run Monte Carlo for one (feed, DO) cell, classify as safe/caution/danger.

    Returns dict with failure_rate, p10_biomass, label.
    'failure' = final biomass below a viability floor OR ethanol overflow
    (Crabtree dominating, i.e. mito product near zero when it shouldn't be).
    """
    if rng is None:
        rng = np.random.default_rng(0)

    finals_X, finals_E, finals_P = [], [], []
    failures = 0
    for _ in range(n_trials):
        p = dict(lab_params)
        p["mu_max"] = max(0.05, rng.normal(lab_params["mu_max"],
                                           lab_sigma["mu_max"] * harshness))
        p["Y_XS"] = max(0.1, rng.normal(lab_params["Y_XS"],
                                        lab_sigma["Y_XS"] * harshness))
        X0_mult = max(0.1, rng.normal(1.0, lab_sigma["X0"] * harshness))
        s0 = list(state0); s0[0] *= X0_mult

        _, sol = simulate(s0, feed, DO_sp, dur=dur, p=p)
        Xf, Sf, Ef, Pf = sol[-1, 0], sol[-1, 1], sol[-1, 2], sol[-1, 3]

        # Contamination event: probability rises with residual glucose
        # (more leftover sugar = more food for contaminants) and with
        # low DO (anaerobic favors lactic acid bacteria). ~2% base.
        contamination_prob = 0.02 + 0.01 * (Sf > 10) + 0.02 * (DO_sp < 30)
        contaminated = rng.random() < contamination_prob
        if contaminated:
            Xf *= 0.3   # contamination crashes the batch

        finals_X.append(Xf); finals_E.append(Ef); finals_P.append(Pf)

        # Failure: weak growth, OR strong ethanol overflow (Crabtree),
        # OR contamination crash
        grew = Xf > s0[0] * 1.8
        overflow = Ef > (Pf + 0.5) * 2.5
        if (not grew) or overflow or contaminated:
            failures += 1

    fr = failures / n_trials
    p10_X = float(np.percentile(finals_X, 10))

    if fr > 0.30:
        label = "danger"
    elif fr > 0.10:
        label = "caution"
    else:
        label = "safe"

    return {
        "feed": feed, "DO": DO_sp,
        "failure_rate": fr,
        "p10_biomass": p10_X,
        "mean_ethanol": float(np.mean(finals_E)),
        "mean_mito": float(np.mean(finals_P)),
        "label": label,
    }


def build_risk_map(state0, lab_params, lab_sigma,
                   feed_grid=None, DO_grid=None,
                   n_trials=60, dur=8.0, harshness=1.5):
    """Build the full risk map across the (feed, DO) grid."""
    if feed_grid is None:
        feed_grid = [0, 4, 8, 12, 16]
    if DO_grid is None:
        DO_grid = [20, 40, 60, 80]
    rng = np.random.default_rng(42)
    cells = []
    for f in feed_grid:
        for d in DO_grid:
            cells.append(classify_cell(state0, f, d, lab_params, lab_sigma,
                                       n_trials=n_trials, dur=dur,
                                       harshness=harshness, rng=rng))
    return cells


if __name__ == "__main__":
    state0 = [3.0, 10.0, 0.5, 0.0, 50.0, 1.0]

    # Lab with no history → literature defaults
    lab_p, lab_s = estimate_lab_params([])
    print("Lab params:", {k: round(v,3) for k,v in
                          [("mu_max", lab_p["mu_max"])]}, "sigma:", lab_s)
    print()

    cells = build_risk_map(state0, lab_p, lab_s, n_trials=40)

    # Print as a grid
    feeds = sorted(set(c["feed"] for c in cells))
    DOs   = sorted(set(c["DO"] for c in cells))
    symbol = {"safe": "GREEN ", "caution": "yellow", "danger": "RED!! "}

    print("RISK MAP (failure rate by feed × DO)")
    print("        DO=20%   DO=40%   DO=60%   DO=80%")
    for f in feeds:
        row = f"feed={f:2d}  "
        for d in DOs:
            c = next(x for x in cells if x["feed"]==f and x["DO"]==d)
            row += f" {symbol[c['label']]}({c['failure_rate']*100:2.0f}%)"
        print(row)
    print()
    print("GREEN = safe (<10% fail), yellow = caution (10-30%), RED = danger (>30%)")
