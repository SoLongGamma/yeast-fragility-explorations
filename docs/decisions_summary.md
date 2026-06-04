# Decisions Summary (1–9)

This document summarizes the meta-level decisions in this project, in
order. Each decision builds on the previous ones and was prompted by
something concrete — usually a result that contradicted an earlier
assumption.

For the *evidence* behind each decision, see `lab_notebook.md`. For
the original full text of decisions 1–6, see `decisions.md`. This
document is the consolidated reading order for someone arriving fresh.

---

## Decision 1 — Build a simulation tool, not run new experiments

Wet-lab access is limited at this stage. A simulation tool that lets
others (or ourselves later) test the central hypothesis under
variability is more useful than a single new wet experiment.

## Decision 2 — Use an agent-based model for the toy version

The hypothesis is about variance and rare events, not averages. ODEs
give one trajectory; ABMs give distributions. Monte Carlo over ABM
seeds is the natural way to ask "what fraction of batches fail?".

## Decision 3 — Frame the target as variance reduction, not yield

Yield optimization is what every existing tool already does. The
reproducibility/variance angle is less crowded and aligns more
directly with the wet-lab pain point (batch-to-batch inconsistency).

## Decision 4 — Adopt Yeast8/ecYeast8 as the metabolic backend

ABM alone is unverifiable without external grounding. Yeast8 is the
Chalmers consensus model and is benchmarked against experimental
chemostat/batch/fed-batch data. ecYeast8 reproduces the Crabtree
effect that Yeast8 cannot; pulse feeding inherently creates glucose
spikes, so Crabtree must be represented.

## Decision 5 — Split tools by role (the structural realization)

Halfway through v0.3 step 2 we tried to run Monte Carlo on ecYeast8
and discovered: ecYeast8 is deterministic. Same inputs → same outputs.
*We were trying to test a variance hypothesis using a model with no
variance.*

Resolution:
- **ABM** = variance backend (Monte Carlo, distributions, antifragility)
- **ecYeast8** = mechanism backend (single trajectories, sanity check)
- They are *not* interchangeable.

## Decision 6 — Stop and write the decisions document

After hours of pushing toward "ecYeast8 + Monte Carlo wrapper," we
recognized the problem wasn't a performance bug. It was a category
error. No amount of speed optimization fixes that. The fix is
structural — and writing it down before more code is the safest move.

## Decision 7 — Spitznagel insurance-betting framing, with caveats

The Spitznagel/Universa "97% asset + 3% American put option" strategy
maps onto bet hedging in microbial populations (Veening 2008, Balaban
2004). The mapping is structurally accurate:

- 3% reserve metabolite pool / pre-primed subpopulation
- The reserve is *American-style*: stress response activates as soon
  as threshold is crossed, not at a fixed maturity
- Output: arithmetic mean ≤ baseline, geometric mean > baseline,
  extinction rate < baseline

Caveat: bet hedging is already a large field. The Spitznagel framing
is structurally familiar, not entirely new. Our specific contribution,
if any, is in the *timing controller*, not in the bet hedging itself.

## Decision 8 — Reframe the model as ESC + event-triggered + dFBA

We initially located our model as MPC (model predictive control).
This was incorrect. The honest position is:

- **MPC** tracks a single reference trajectory continuously.
- Our model is **state-based triggering**: act when state crosses a
  threshold, not on a fixed schedule.

The accurate placement is:
- **Backbone**: dFBA / DFBM (e.g., Chang Liu Henson 2016)
- **Search**: Extremum Seeking Control (Krstic & Wang 2000)
- **Action**: Event-triggered control with prophylactic perturbations

Our potential contribution is *risk-constrained ESC for yeast
fed-batch reproducibility*. This is narrower than the original framing
but defensible.

## Decision 9 — Standardize on academic terminology

Project-internal intuitive terms (e.g., "variance cleanup",
"insurance betting") are mapped onto academic standard terms so the
project is legible to outside readers:

| Internal | Academic |
|---|---|
| 변수 청소 / variance cleanup | variance reduction / phenotypic synchronization |
| 간헐 자극 / intermittent stimulus | intermittent prophylactic perturbation |
| 보험 베팅 / insurance bet | bet hedging |
| 호르메시스 / hormesis | stress priming / preconditioning |
| 허용 envelope / acceptable envelope | design space (ICH Q8) |
| extinction rate | culture failure rate |
| black swan | rare disturbance / tail event |

Two-audience elevator pitches:
- **For yeast/bioprocess audience**: "Open-source fed-batch
  recommendation tool focusing on reproducibility under
  inoculum-size variability, using statistical safeguards (bootstrap
  CI, multiple-comparison correction)."
- **For Taleb/Axenie-adjacent audience**: "ABM with explicit
  Monte Carlo over input distributions, measuring antifragility as
  right-tailed output distribution under environmental variance."

## Current Position

- v0.1 ABM with Monte Carlo (Phase A heavy: 8000 trials, culture
  failure rate −41%p in variable schedule)
- v0.2 statistical safeguards and data infrastructure
- v0.3 ecYeast8 backend (Crabtree confirmed, single trajectories)
- v1.0 MVP (Streamlit, 5-state ODE, feed/DO recommendation)
- Simple Monte Carlo on 5-state ODE (N=200, ethanol CV 20% from 3
  parameter perturbations of 10–15%)

## What is and is not validated

**Validated:**
- ecYeast8 Crabtree threshold matches published chemostat data
- Pulse schedule reduces culture failure rate in toy ABM
- Small input perturbations (10–15%) produce ~2× variance
  amplification in downstream metabolite (ethanol) — consistent
  with published sensitivity analysis

**Not validated:**
- Whether toy ABM behavior transfers to real yeast cells
- Whether MVP recommendations would help an actual fed-batch operator
- Whether bet hedging timing improves geometric mean yield in practice
