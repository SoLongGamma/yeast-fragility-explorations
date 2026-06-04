"""
Simplest Monte Carlo on the 5-state ODE.

Sample 3 most impactful parameters (mu_max, X0, Y_XS) from normal
distributions, simulate N=200 fed-batch runs under a fixed schedule,
look at the distribution of final ethanol.

That's it. No optimization, no comparison — just "what does the
output distribution look like under realistic input variance?"
"""

import sys
sys.path.insert(0, '/home/claude/yeast_mvp')

import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
from model import simulate, PARAMS

N_TRIALS = 200
DURATION_H = 40.0
FEED_RATE  = 10.0       # g/L/hr  — fixed feed
DO_SETPT   = 60.0      # %       — fixed DO

rng = np.random.default_rng(42)

results = []
for trial in range(N_TRIALS):
    # Sample 3 dominant uncertainty sources
    params = dict(PARAMS)
    params["mu_max"] = max(0.05, rng.normal(0.40, 0.06))   # ±15%
    params["Y_XS"]   = max(0.10, rng.normal(0.50, 0.05))   # ±10%
    X0               = max(0.1,  rng.normal(2.0,  0.30))   # ±15% inoculum

    initial_state = [X0, 20.0, 0.0, 80.0, 1.0]   # X, S, E, DO, V
    _, sol = simulate(initial_state, FEED_RATE, DO_SETPT,
                      duration_h=DURATION_H, params=params)
    final = sol[-1]
    results.append({
        "trial": trial,
        "mu_max": params["mu_max"],
        "Y_XS":   params["Y_XS"],
        "X0":     X0,
        "X_final": final[0],
        "S_final": final[1],
        "E_final": final[2],
    })

# Pull final ethanol distribution
E_finals = np.array([r["E_final"] for r in results])
X_finals = np.array([r["X_final"] for r in results])

print("="*60)
print(f"Monte Carlo on 5-state ODE  (N={N_TRIALS})")
print(f"Fixed: feed={FEED_RATE} g/L/hr, DO={DO_SETPT}%, duration={DURATION_H}h")
print(f"Sampled (Normal): mu_max=0.40±0.06, Y_XS=0.50±0.05, X0=2.0±0.30")
print("="*60)
print()
print("Final ethanol distribution:")
print(f"  mean   = {E_finals.mean():.2f} g/L")
print(f"  std    = {E_finals.std():.2f} g/L")
print(f"  median = {np.median(E_finals):.2f} g/L")
print(f"  p10    = {np.percentile(E_finals, 10):.2f} g/L")
print(f"  p90    = {np.percentile(E_finals, 90):.2f} g/L")
print(f"  CV     = {E_finals.std()/E_finals.mean()*100:.1f}%")
print()
print("Final biomass distribution:")
print(f"  mean   = {X_finals.mean():.2f} g/L")
print(f"  std    = {X_finals.std():.2f} g/L")
print(f"  CV     = {X_finals.std()/X_finals.mean()*100:.1f}%")

# Histogram
fig, axes = plt.subplots(1, 2, figsize=(11, 4))
axes[0].hist(E_finals, bins=25, color="crimson", alpha=0.75, edgecolor="black")
axes[0].axvline(E_finals.mean(), color="black", ls="--",
                label=f"mean={E_finals.mean():.1f}")
axes[0].axvline(np.percentile(E_finals, 10), color="grey", ls=":",
                label=f"p10={np.percentile(E_finals,10):.1f}")
axes[0].axvline(np.percentile(E_finals, 90), color="grey", ls=":",
                label=f"p90={np.percentile(E_finals,90):.1f}")
axes[0].set_xlabel("Final ethanol (g/L)")
axes[0].set_ylabel("count")
axes[0].set_title(f"Ethanol distribution (N={N_TRIALS})")
axes[0].legend()

axes[1].hist(X_finals, bins=25, color="steelblue", alpha=0.75, edgecolor="black")
axes[1].axvline(X_finals.mean(), color="black", ls="--",
                label=f"mean={X_finals.mean():.1f}")
axes[1].set_xlabel("Final biomass (g/L)")
axes[1].set_ylabel("count")
axes[1].set_title(f"Biomass distribution (N={N_TRIALS})")
axes[1].legend()

plt.tight_layout()
plt.savefig('/home/claude/mc_simple.png', dpi=110, bbox_inches="tight")
print()
print("Histogram saved -> /home/claude/mc_simple.png")
