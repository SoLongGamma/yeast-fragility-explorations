# Decisions

This document records the meta-level decisions behind this project — not what
the code does, but *why* it does it that way. Each section captures a moment
where a choice was made between paths, including the reasoning, the rejected
alternatives, and what we still don't know.

The point isn't to defend the decisions. It's to make them inspectable, so
future-me (or anyone else) can see whether they still make sense.

---

## Decision 1 — Why simulate at all?

**Context.** Yeast fermentation reproducibility is a known industry problem.
Many proposed solutions exist: better SOPs, online sensors, single-cell QC,
strain stabilization (e.g., Kim et al. 2015 on spermidine-modulated tolerance).

**Decision.** Build a *simulation tool* that lets the user compare feeding
schedules under variability and shocks, rather than running new wet-lab
experiments or proposing a new strain.

**Why this and not other paths.**
- Wet-lab experiments: not available to the project initiator at this stage.
- Strain engineering: well-covered by groups like the advisor's; not where a
  new contribution from this project is likely.
- Pure literature review: lower utility than a *tool* others can use.

**What we accept by this choice.**
- Any conclusion is limited to "what the model says," not "what cells do."
- The tool's value depends on its assumptions being defensible.

**Open question.** Whether a simulation tool moves the needle in practice
depends entirely on whether yeast researchers find it useful. This is
unanswered until at least one such person has used it on their own data.

---

## Decision 2 — Why agent-based, not ODE?

**Context.** Standard fermentation modeling uses ODEs (e.g., Monod kinetics
for biomass and substrate). Agent-based models (ABMs) are heavier but
preserve individual cell heterogeneity.

**Decision (v0.1).** Use a coarse ABM for the toy model. Each agent has
biomass, defense capital, intrinsic robustness.

**Why this and not ODE.**
- The central hypothesis is about *variability and rare events*, not
  averages. ODEs give a single trajectory; ABMs give a distribution.
- Hormesis as we framed it depends on *cell-to-cell* differences in defense
  state, which is invisible in an ODE.
- Monte Carlo over ABM seeds gives us a natural framework for the
  reproducibility metric (variance of final outcome across seeds).

**What we accept by this choice.**
- ABM parameters are abstractions (defense capital is not a measurable
  quantity). The model is for *qualitative insight*, not quantitative
  prediction.
- Calibration to real data is fundamentally harder than for ODE-based GEMs.

**Open question.** Whether the qualitative patterns ABM shows transfer to
real cells. Answering this requires either:
- replicating the patterns in a validated model (Yeast8/ecYeast8), or
- direct comparison to real fermentation data.

Both have proven harder than expected (see decisions 5 and 6).

---

## Decision 3 — Why "variance cleanup" as the framing?

**Context.** Many ways to frame the central hypothesis: hormesis,
anti-fragility, self-cycling fermentation, cross-protection, phenotypic
synchronization. All exist in the literature with overlapping but distinct
meanings.

**Decision.** Use *variance reduction* / *reproducibility* as the
operational target, not yield or robustness in the usual sense.

**Why this and not "yield optimization".**
- Yield optimization is what every other tool already does. Yeast8 in
  particular is optimized for yield prediction.
- The reproducibility/variance angle is *less crowded* in the literature
  and aligns more directly with the wet-lab pain point (batch-to-batch
  inconsistency) than with the bioreactor-design pain point (titer).

**Why this and not "yield + reproducibility".**
- Performance-robustness trade-off is documented (Life Science Alliance
  2024, 24-strain study). Trying to optimize both simultaneously is a
  legitimate goal but a *much* harder framing to defend.
- Picking *one* metric and admitting the trade-off is more honest than
  pretending both can be maximized.

**Open question.** Whether yeast researchers in practice care about
batch-to-batch variance enough to use a tool focused on it. The hypothesis
is yes, but this needs validation by talking to one.

---

## Decision 4 — Why Yeast8 / ecYeast8 as backend?

**Context.** Several genome-scale models exist for *S. cerevisiae*. Yeast8
is the consensus model maintained by the Chalmers group. ecYeast8 adds
enzyme-capacity constraints; pcGEMs add proteome-allocation constraints.

**Decision.** Adopt the Yeast8 family as the canonical metabolic backend.

**Why this and not "stick with the toy ABM".**
- The ABM is unverifiable without external grounding. Yeast8 has been
  benchmarked against experimental chemostat / batch / fed-batch data
  (Domenzain et al., Microbial Biotechnology 2022).
- When a yeast researcher asks "why should I trust your model?", pointing
  to Yeast8 papers is a defensible answer; pointing to our own ABM is not.
- Yeast8 is open-source SBML; no licensing barrier.

**Why ecYeast8 over Yeast8.**
- Yeast8 alone does not predict the Crabtree effect (the model has no
  proteome capacity constraint, so overflow metabolism doesn't emerge).
- ecYeast8 reproduces Crabtree under glucose excess (verified ourselves
  during the v0.3 step 2 spike — ethanol secretion appears above
  ~5–8 mmol/gDW/hr glucose uptake, matching literature).
- Pulse feeding inherently creates glucose spikes; without Crabtree being
  represented, we'd be hiding a key trade-off.

**What we accept by this choice.**
- Both models are *deterministic*. Given the same inputs, they return the
  same outputs every time. Variance must come from a Monte Carlo wrapper.
- ecYeast8 simulations are computationally heavy (8144 reactions, ~1.5s
  per FBA solve, ~2 min per dFBA run, ~2 hours per Monte Carlo sweep of
  N=30 trials × 2 schedules). This is a real constraint on the interactive
  notebook experience.
- Yeast8/ecYeast8 has no representation of *stress response gene
  expression*, *memory between feeds*, or *cell-to-cell heterogeneity*.
  Hormesis as we hypothesize it cannot appear *intrinsically* in these
  models — it must come from how we wrap them.

**Open question.** Whether there is a published Yeast8 extension that
*does* model stress response (the candidate is Resource Balance Analysis
models like scRBA, but their complexity is currently above this project's
budget).

---

## Decision 5 — The structural mismatch nobody warned us about

**Context.** Halfway through v0.3 step 2 we ran ecYeast8 with both
constant and pulsed feed and got a clean answer: constant gives 66 g/L
biomass, pulse gives 35 g/L. *And the same numbers every time.*

**This is the moment the project nearly went off the rails.** We were
trying to test a hypothesis about *variance reduction* using a model that
*has no variance*. The numerical answer was real but it answered a
different question than ours.

**Decision.** Acknowledge the mismatch explicitly. Two tools, two roles:

| Question | Right tool |
|---|---|
| Does pulse change *mean* biomass / ethanol / metabolic state? | ecYeast8, single trajectory |
| Does pulse reduce *variance* across trials? | Monte Carlo wrapper over ANY dFBA |
| Does the hormesis mechanism (defense + memory) make a difference? | ABM (v0.1/v0.2) — Yeast8 doesn't model this |
| Can we trust the ABM's mechanistic claims? | Sanity-check against ecYeast8 mass-balance predictions |

**Why this and not "force one tool to do both".**
- Forcing Yeast8 dFBA to do Monte Carlo: technically possible, costs hours
  per run, and the variance comes entirely from the *wrapper's parameter
  sampling*, not from the biology. This conflates "model parameter
  uncertainty" with "real biological variability".
- Forcing ABM to be quantitative: requires calibration data we don't have.

**What we accept by this choice.**
- The project now has *two* models, not one. The README has to explain
  which is for which. This is a documentation burden but also a research
  honesty.
- Final conclusions on the hormesis hypothesis will come from the ABM
  (with Monte Carlo built in), grounded by ecYeast8 single-trajectory
  checks for mechanistic plausibility — not from running Monte Carlo on
  ecYeast8 itself.

**Open question.** Whether a hybrid representation (ABM cells with
metabolism defined by per-cell mini-FBA on a reduced Yeast8) is worth the
engineering effort. Probably yes in v0.5+, definitely no now.

---

## Decision 6 — Why stop and write *this* document instead of writing more code?

**Context.** After hours of building toward "v0.3 step 2: ecYeast8 + Monte
Carlo wrapper", we found that the wrapper would take ~2 hours per run on
Colab free tier. We could have pushed through by reducing N, dt, or the
model. Instead we stopped.

**Decision.** Write the meta-document (this file) before any more code.

**Why this and not "just make it work".**
- The reason the simulation kept taking longer than expected wasn't a
  performance bug. It was a *category error*: trying to test a variance
  hypothesis with a model that has no variance. No amount of speed
  optimization fixes that. The fix is structural.
- A project at this stage has more code than its author can hold in mind.
  Future-me will not remember why ecYeast8 isn't the Monte Carlo backend
  unless this is written down. Without this document, future-me would
  rediscover the same dead end.
- Talking to an advisor or peer about the project requires being able to
  *explain the architecture in 3 sentences*. Until that's possible, more
  code makes the explanation harder, not easier.

**What we accept by this choice.**
- One day of no new code. The repo will look unchanged on Github except
  for this file.

**What we get in return.**
- A clear contract for v0.4 onward: ABM is the variance backend, Yeast8/
  ecYeast8 is the mechanism backend, and they are *not interchangeable*.

---

## What this project is, as of now (one-paragraph summary)

A toy ABM (v0.1/v0.2) tests the hypothesis that intermittent stress
reduces batch-to-batch variance in yeast fermentation outcomes — the
"variance cleanup" framing of hormesis. Statistical safeguards (Bonferroni
correction, search-inflation warnings) are built in to guard against the
multiple-comparison illusion. Yeast8 / ecYeast8 (v0.3) is used as a
*mechanistic sanity check*, single trajectories at a time, to verify that
the ABM's qualitative predictions (e.g., that pulse feeding causes
Crabtree overflow under realistic uptake limits) don't contradict
validated metabolic constraints. Both tools serve the same hypothesis
from different angles; neither replaces the other.

The honest current status: the framework works, the hypothesis remains
testable but unvalidated against real wet-lab data, and the next critical
step is feedback from someone who actually does yeast fermentation
experiments.

---

## What's still undecided

- **Whom to show first.** Sequence and timing of presenting to advisor /
  former lab senior / outside experts. (See `docs/communication.md` if
  it exists; otherwise this is held in the project initiator's head.)
- **Whether to publish a preprint, or keep it as a portfolio piece.**
- **Whether to extend to other species** (P. pastoris, Y. lipolytica) or
  stay focused on *S. cerevisiae*.
- **What "v1.0" means.** Not yet defined. Probably involves at least one
  wet-lab dataset used in calibration, and at least one third party
  having opened the tool.
