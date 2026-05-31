# Lab Notebook — what we actually saw

This is the companion document to `decisions.md`. Where decisions.md
records *why* we chose paths, this file records *what we ran and what
came back*. The two read in parallel.

The experiments below were run inside an analysis container during a
conversation in late May 2026 — the same container where the v0.3
notebook scaffolding was written. None of this is meant to be a final
result; it's the data the structural decisions were based on. If any
result here turns out wrong, the corresponding decision should be
revisited.

All numbers below come from actual runs against:
- Yeast-GEM v9.0.x (downloaded fresh from
  `https://github.com/SysBioChalmers/yeast-GEM`, 11.2 MB, 4131 reactions)
- ecYeastGEM_batch (downloaded fresh from
  `https://github.com/SysBioChalmers/ecModels`, 9.3 MB, 8144 reactions)
- COBRApy as installed by `pip install cobra` at that time

---

## Experiment 1 — Does Yeast8 even load?

**Why we ran it.** Before assuming Yeast8 is the right backend, verify
the file loads and the default FBA returns a biologically plausible
answer.

**What we ran.**
```python
import cobra
model = cobra.io.read_sbml_model('yeast-GEM.xml')
sol = model.optimize()
```

**What came back.**
```
Reactions:   4131
Metabolites: 2806
Genes:       1161
Default growth rate (mu): 0.0858 /hr
```

**Interpretation.** 0.086 /hr is in the right range for *S. cerevisiae*
chemostat growth — typical experimental values run 0.05–0.3 /hr depending
on conditions. The model isn't broken.

**Why this matters for the project.** It rules out the trivial failure
mode ("the model is just wrong from the start"). It does *not* validate
anything about fed-batch dynamics yet.

---

## Experiment 2 — Naive dFBA on Yeast8 produces nonsense

**Why we ran it.** To build a dynamic FBA loop (Monod uptake → FBA → 
update biomass and glucose → repeat) on top of Yeast8, matching how a
batch fermentation actually unfolds.

**What we ran.** A 40-hour batch simulation with initial biomass 0.1 g/L,
initial glucose 20 g/L, dt = 0.5 h, v_max_uptake = 10 mmol/gDW/hr.

**What came back.**
```
At t=6h, glucose depleted, FBA infeasible — simulation stopped.
Final biomass at t=6h: 15.98 g/L (started from 0.1 g/L)
Final ethanol: 0.00 g/L
```

**What that meant.** Two failure modes:

1. **Biomass overshoot.** Going from 0.1 to 16 g/L in six hours implies
   doubling time well under one hour. Real *S. cerevisiae* doubles in
   about 90 minutes under good conditions. The simulation was running
   too fast.
2. **Zero ethanol.** Yeast8 returned no ethanol secretion under any
   condition we ran. This is exactly the Crabtree effect that Yeast8
   *cannot* represent without enzyme capacity constraints.

**Why this matters for the project.** This is the first concrete sign
that Yeast8 alone is insufficient for our purpose. It can't show
overflow metabolism, which is exactly the dynamic we care about during
glucose spikes from pulsed feeding.

---

## Experiment 3 — Fixing the dFBA loop

**Why we ran it.** To get a sensible trajectory before doing anything
fancier.

**What we changed.**
- Reduced `v_max_uptake` from 10 to 3.5 mmol/gDW/hr (realistic fed-batch
  value).
- Added a crude density-dependent factor `(1 - x/X_max)` applied to both
  uptake and growth rate, with X_max = 80 g/L. This is a stand-in for
  the many real-world limits (oxygen transfer, byproduct inhibition,
  physical crowding) that Yeast8 dFBA does not represent.

**What came back (constant feed, 40 h, 80 g total glucose, batch phase
ends at 8 h).**
```
Final biomass: 46.0 g/L
Glucose trajectory: 15.0 → 6.3 → 0.0 → 0.0 g/L
```

**Interpretation.** The trajectory is now plausible. Yeast grows through
the batch phase, glucose depletes, the constant feed maintains a low
steady state.

**Why this matters for the project.** The dFBA loop is now usable. But
the fix exposed how much *we* are imposing on the model — the density
factor in particular is our scaffolding, not Yeast8's biology. If
anything in v0.4+ depends on it, that has to be called out.

---

## Experiment 4 — Yeast8, pulse vs constant, single trajectory

**Why we ran it.** First direct test of the central hypothesis on a
validated backend: does pulse feeding give a different outcome from
constant feeding, holding total glucose delivered equal?

**What we ran.**
- Constant: 4 g/L/hr starting at t=8h
- Pulse: triangular peaks at 12 g/L/hr, 2 h wide, every 6 h, starting
  at t=8h
- Both scaled to deliver exactly 80 g total glucose

**What came back.**
```
                Constant    Pulse
Final biomass    46.0       39.3 g/L      (-14.4%)
Starvation time  35%        48%
Mean glucose     1.3        2.4 g/L
```

**Interpretation.** Pulse loses about 14% of biomass under Yeast8. Two
explanations:

1. **Mechanistic.** Pulses create periods of low/zero glucose, so the
   cells spend more time at zero growth. The lost time is real.
2. **Missing biology.** Yeast8 has no stress-response or memory. A real
   yeast cell that gets pulsed might *anticipate* the next pulse — by
   pre-allocating defense proteins, by maintaining higher trehalose
   pools, etc. Yeast8 can't model that.

The 14% gap is what Yeast8 *can* see. Whatever hormesis contributes
(positive or negative) is invisible at this resolution.

**Why this matters for the project.** This was a foreseeable result; we
ran it anyway to ground the analysis in real numbers. The takeaway
isn't "pulse is bad" — the takeaway is "Yeast8 alone can't decide for
us." That's why we considered ecYeast8 next.

---

## Experiment 5 — Does ecYeast8 actually show Crabtree?

**Why we ran it.** The whole argument for switching to ecYeast8 rests
on it predicting Crabtree overflow under glucose excess. Verify the
prediction *exists* before building anything on top.

**What we ran.** Loaded ecYeastGEM_batch and ran FBA at glucose uptake
upper bounds from 1 to 20 mmol/gDW/hr (the uptake reaction in ec models
is `r_1714_REV`, not `r_1714`).

**What came back.**
```
v_glc_max   mu      v_etoh   Crabtree?
  1.0      0.087     0.000     no
  2.0      0.177     0.000     no
  3.0      0.267     0.000     no
  5.0      0.331     0.000     no
  8.0      0.354     2.860     YES  ← critical uptake threshold
 10.0      0.361     9.481     YES
 15.0      0.376    23.716     YES
 20.0      0.377    29.567     YES  ← overflow regime
```

**Interpretation.** Below roughly 5 mmol/gDW/hr glucose uptake, ecYeast8
predicts pure respiration with no ethanol. Above 8, ethanol secretion
takes off rapidly. This is exactly the published behavior of
Crabtree-positive *S. cerevisiae* in chemostat experiments, where the
critical dilution rate D_crit at which fermentation kicks in falls in
the 5–8 mmol/gDW/hr region.

**Why this matters for the project.** ecYeast8 reproduces a published,
non-trivial phenomenon that Yeast8 cannot. We have a defensible reason
for the heavier model.

---

## Experiment 6 — ecYeast8, pulse vs constant, single trajectory

**Why we ran it.** Repeat Experiment 4 on the better backend.

**What came back (same schedules as Experiment 4).**
```
                Constant    Pulse
Final biomass    65.6       34.7 g/L     (-47.1%)
Final ethanol     3.1        6.5 g/L     (+108%)
Max glucose       1.2        6.9 g/L
Min glucose       0.0        0.0 g/L
Glucose std       0.62       1.64 g/L
```

**Interpretation.** Compared to Yeast8:
- The biomass gap *widens* from -14% to -47%. The mechanism is the
  Crabtree effect — pulses push instantaneous uptake above the
  fermentation threshold, so much of the pulsed glucose is converted
  to ethanol instead of biomass.
- Ethanol production *doubles* under pulse. From an industrial
  bioethanol standpoint, this is the *desirable* direction. From a
  biomass-yield standpoint, it's a loss.

**Why this matters for the project.** Pulse vs. constant isn't a single
hypothesis — it's a *trade-off depending on the target product*. Our
framing of "reproducibility" still hasn't been touched by either
experiment; both Yeast8 and ecYeast8 returned exactly one number per
condition.

This is the experiment that triggered Decision 5 (the structural
realization).

---

## Experiment 7 — Attempting Monte Carlo on Yeast8

**Why we ran it.** To verify whether the Monte Carlo wrapper plan
(N=30 trials per schedule, sampling Ks, v_max, initial biomass and
glucose from distributions) was computationally feasible within Colab.

**What happened.** The run timed out at the container's 15-minute
limit. Estimated full run time: 40+ minutes for Yeast8, 2+ hours for
ecYeast8.

**Interpretation.** The wrapper idea is correct; the choice of backend
isn't. ecYeast8 + Monte Carlo is the right *shape* and the wrong
*runtime*. Yeast8 + Monte Carlo is feasible but loses Crabtree.

**Why this matters for the project.** This was the prompt for the
two-tool split in Decision 5. Once we accepted that we don't need
Yeast8/ecYeast8 *to provide* variance — we just need them as
mechanistic checks on single trajectories — the runtime problem
dissolves. The variance side of the project belongs to the ABM, where
it was already running comfortably in v0.2.

---

## What this lab notebook is for

If you're reading this in `docs/lab_notebook.md`, you've seen the
ground truth: a few hours of bench-test simulation that pointed us at
the right architecture only after pointing us at three wrong ones.

The pattern across all seven experiments is the same: *the simulation
returned what the model could return, and the question became whether
that answer was what we'd asked.* Pulse causes Crabtree overflow — yes,
real, in the literature. But that's a *mean shift*, not a *variance
shift*, and the hypothesis was about variance.

The lesson encoded in `decisions.md` (especially Decision 5) is what
this notebook is the evidence for.
