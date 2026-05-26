# Roadmap

If real wet-lab data ever becomes available — for example, fed-batch
data from a friendly yeast lab — there are three plausible directions
this project could take. They differ in **how much data is needed**,
**how likely they are to produce something useful**, and **how big the
payoff is if they succeed**.

The right order is **A → B → C** (sequential, not parallel), because A
is the cheapest deliverable and earns the trust needed to ask for the
data B and C require.

---

## Path A — Calibration

**Question:** Given the *specific* yeast strain a lab uses, what
parameters in the ABM should be set to match their actual fermentation
behavior?

**Data needed:** 3–5 fed-batch runs at different feed rates, with at
least final product titer. Ideally time-series of biomass and glucose.

**Deliverable:**
- A `calibrated_params_<lab>.json` file: the lab's strain in numbers
  (μ_max, K_s, yield coefficient, etc.).
- A "Lab Mode" in YeastFort that scores protocols against *their*
  strain, not generic *S. cerevisiae*.
- A simple residual plot (predicted vs. measured) as honesty signal.

**Risk:** Low. Even modest data gives a useful fit. Failure mode is
just "more data needed."

**Time:** 3–5 days after data arrives.

**Honest value to a lab:** Modest. This is essentially restating their
own data back to them in different units. Useful as a trust-building
first step, not as a result.

---

## Path B — Prediction

**Question:** Given a calibrated model of the lab's strain, can we
predict which *unseen* feed schedules would work well — and route the
lab away from wasted experimental runs?

**Data needed:** Path A's calibration data. Optionally, one or two
pulsed-feeding runs as held-out validation.

**Deliverable:**
- A protocol search tool: input objective (yield / robustness / both),
  output a ranked list of feed schedules with predicted outcomes and
  fragility scores.
- Most usefully: "Of these 100 schedules you have not tried, here are
  the 5 we predict will be most reproducibility-improving."
- **Held-out validation** is essential. Without it, this is just
  in-sample fitting wearing a hat.

**Risk:** Medium. Models interpolate well, extrapolate poorly. A
schedule far from anything in the training data may produce a wrong
prediction. Mandatory labeling: "screening tool — verify in lab."

**Time:** 1–2 weeks after calibration.

**Honest value to a lab:** Significant. Answers the question "what
should I try next?" Even if only one in five recommended protocols
works, that is still a useful filter compared to guessing.

---

## Path C — Reproducibility postmortem

**Question:** When the same protocol gives different results across
replicates, *where* in the trajectory does the divergence originate,
and what hidden variable is responsible?

**Data needed:** **Replicate** runs of the same protocol — minimum
n=5, ideally n=10+, with time-resolved measurements per run. This is
the hardest data to obtain because most labs do not publish or even
keep this in usable form.

**Deliverable:**
- A "trajectory divergence" analysis: identify the tick at which
  replicate runs begin to separate.
- Match that timing to environmental conditions in the ABM to localize
  the suspected hidden variable.
- Output: "Your reproducibility problem most likely originates from
  initial inoculum heterogeneity at tick X, with 67% confidence."
- Actionable recommendations: "Tighten pipetting tolerance to ±Y%."

**Risk:** High. If replicate data is sparse or noisy, the analysis
will be inconclusive. Many labs simply do not have what is needed.

**Time:** 2–4 weeks. Quality of result depends on quality of data.

**Honest value to a lab:** Potentially largest. Directly addresses the
problem motivating this project in the first place — *why does the
same experiment give different results.* But success is not
guaranteed.

---

## Why this order matters

Path A produces a deliverable with high probability. Showing it to a
lab earns the trust needed to ask for the more demanding data that B
and C require. Asking for Path C's replicate data on the first contact
is a much bigger ask than asking for Path A's data — but after Path A
is done, the ask becomes natural.

This is a **trust ladder**, not a feature backlog.

---

## What none of these paths can do

- Replace wet-lab validation. Every output of every path remains a
  prediction until tested at the bench.
- Generalize across strains without re-calibration. A strain that has
  not been through Path A should be treated as out-of-distribution.
- Account for failure modes the model does not represent (mechanical
  failures, novel contaminants, operator error).

---

## A note about who builds this

If any of A / B / C actually happens, the right team is not one person
prompting an LLM. It is one person prompting an LLM in close
collaboration with one experimentalist who runs the wet-lab side. The
LLM-only version of this project, as currently constituted, is a
demonstrator. The next version, if there is one, needs a partner with
a fermenter.
