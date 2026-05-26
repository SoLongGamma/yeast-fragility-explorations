# Self-critique of v0.1

This is a list of things wrong with v0.1 that I am aware of. If you spot
more, please open an issue.

The reason this document exists is simple: a hostile reviewer would
notice these things anyway. Naming them first is more honest and saves
everyone time.

---

## Hidden assumptions that make "variable wins" nearly inevitable

### 1. The lethal threshold is a function of defense capital

In `yeast_agent.py`:

```python
upper = T_LETHAL_HIGH + 4.0 * self.defense * self.intrinsic_robustness
survivable_toxin = 0.3 + 0.9 * self.defense * self.intrinsic_robustness
```

Defense expands the survivable band directly and linearly. Variable
environments build defense via hormesis; constant environments do not.
Therefore variable cells survive black-swan shocks. This is closer to a
**restatement of the hypothesis** than a test of it.

A genuine test would require defense to confer survival via some
mechanism that is not itself the definition of "antifragile cell
survives shock."

### 2. The hormesis window is hand-picked

```python
if 0.15 < s < 2.0:
    self.defense += 0.05 * s
elif s <= 0.15:
    self.defense -= 0.02
```

The variable environment's stress score sits squarely inside this
window. The constant environment's stress score is below it. **The
boundaries were chosen — not derived from anything — and they happen to
separate the two regimes exactly.** No sensitivity sweep on these
boundaries has been done. Changing `0.15` to `0.5` and `2.0` to `0.6`
might invert the result.

### 3. Maternal inheritance compounds the advantage

`daughter_defense = 0.7 * mother_defense`. Over many generations the
variable population accumulates a head start in defense that the
constant population structurally cannot. This was added as a biological
courtesy (epigenetic memory) but it amplifies the rigging.

### 4. The "constant" regime is a strawman

The constant regime is held at the *biological optimum* (30°C / pH 5 /
glucose ample). Real industrial constant protocols run at sub-optimal
points and would accumulate some baseline stress response. Comparing
a real-world variable protocol against a textbook-optimal constant
protocol is unfair.

### 5. "Same mean" is arithmetically true but biologically false

The variable schedule averages to 30°C (4 ticks at 37°C, 8 ticks at
26.5°C). Arithmetic mean = 30°C. But yeast growth response to
temperature is non-linear (Arrhenius-like), so the **effective**
biological mean differs from the arithmetic mean. The fair-comparison
claim does not survive this correction.

---

## What I have done to test the model honestly

### P0-2: Swan timing sweep ✓

`v0.1/results/p0_swan_timing_sweep.png` — the variable regime's
advantage **collapses** when the contamination event fires before
defense capital has had time to build (tick 5: advantage ≈ 4
percentage points; tick 50+: advantage ≈ 34 pp). This is at least
directionally honest: the model does not claim variable always wins,
only that it wins after priming.

This is the one ablation that did not turn the project into rubble.

---

## What I have NOT done

These remain open. They are listed in roughly decreasing order of
how much they would damage the project if they came back unfavorable.

### P0-1: Defense ablation (most important)

Remove the `defense` scalar entirely. Keep only `intrinsic_robustness`
(per-cell variation, drawn at birth). Does the variable regime still
win? If yes, the entire "antifragility / hormesis" frame is unnecessary
— variance-induced selection alone explains the result, and the model
should be rebranded. If no, the frame is at least mechanistically
loadbearing.

### P0-3: Effective-mean correction

Recompute the variable schedule so that the *biological* time-average
of temperature (weighted by growth-rate response) equals the constant
regime's temperature, rather than the *arithmetic* time-average. Does
the effect survive?

### P1: Hormesis-window sensitivity

Sweep the (lower, upper) bounds of the hormesis window across a wide
grid. Plot the region of parameter space where variable wins. If that
region is <10% of the grid, the v0.1 result is a cherry-pick.

### P2: Null bimodality check

Fix `defense = 0` for all cells. Feed fat-tailed contamination events
only. Is the outcome distribution still bimodal? If yes, the bimodality
in fig2 is a property of fat-tail inputs, not of fragility per se.

### P3: Mechanism identifiability

Compare three plausible models that all reproduce the macroscopic
signal (extinction gap, bimodality):

- (A) trained defense capital — the current model
- (B) phenotypic heterogeneity + selection only
- (C) stochastic dormancy switching (bet-hedging)

If all three reproduce the data, the model is **unidentifiable** from
the macroscopic signal alone and "antifragility" is no more supported
than the alternatives.

### P4: Sustained insult

The current black swan is a single-tick toxin pulse. Real contamination
events build over many hours. Replace with sustained insult and check
whether defense capital is depleted faster than it can help.

### P5: Carrying-capacity boundary effects

Surviving variable trajectories all plateau at the carrying capacity
(~3000). Raise the cap to 10,000 and check that the effect size is not
a boundary artifact.

---

## What a hostile peer reviewer would say

Reviewer 2 (Nature, paraphrased):

> The authors report a 33-percentage-point difference in extinction rate
> between variable and constant regimes. This result is a direct
> consequence of the model's structural assumptions, not a discovery.
> The lethal threshold is an explicit function of defense capital;
> defense capital accumulates only under stress; the variable regime
> provides stress; therefore the variable regime survives. There is no
> ablation of the defense mechanism, no parameter sensitivity, no
> comparison to plausible null models. **Reject.**

Reviewer 2 would not be wrong about any of this.

---

## What v0.1 actually contributes (best honest case)

A clean, runnable demonstration of what a hormetic-priming hypothesis
looks like in simulation, with one ablation (swan timing) showing the
model is not trivially rigged in *that* dimension, and an explicit
public list of the dimensions where it might still be rigged.

That is a useful starting point for a real research program. It is not
a result.

---

## What would change my mind

The model would graduate from "toy that illustrates the hypothesis" to
"toy that supports the hypothesis" if P0-1, P0-3, and P1 all came back
favorable. None of those have been done yet.
