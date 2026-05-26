# v0.1 design notes

Notes-to-self about why the code looks the way it does. Not for the README.

## Why ABM instead of ODE

The whole story is about individual cells diverging from the population
average under hidden noise. An ODE smooths exactly the thing we want to see.
The `intrinsic_robustness` field on each `YeastAgent` is the in-silico
analogue of "two cells from the same colony aren't actually identical".

## Same-mean comparison

For the Jensen claim to be honest, the two regimes have to share the same
time-averaged temperature, glucose, and pH. The `VariableEnvironment` square
wave is mean-preserving (4 hot ticks balanced by 8 cooler-than-optimal ticks
below 30 °C). The glucose pulse interval × bolus magnitude was tuned so the
time-average equals the constant-feed value. If you change one regime's
amplitude, re-check the mean.

## Defense costs growth

`realized_growth *= (1 - 0.3 * defense)` is critical. Without it, defense is
free insurance and the result becomes trivial. The point is that defense
trades yield-per-tick for survival probability. That's the Talebian
"skin in the game" — insurance is a cost, and we should still want to pay it.

## Black swan = half-Cauchy

Half-Cauchy gives most draws in the 0–1 range with rare excursions past 5.
That matches the qualitative picture of "most days nothing happens; once in
a while everything goes wrong at once". A Gaussian would lose the bimodality
that shows up in fig2.

## Mesa 3.x footguns hit during build

1. `Agent.__init__(model)` auto-registers the agent into `model.agents`.
   This broke the first carrying-capacity implementation because a daughter
   was already in the agent list before our cap check ran. Fix: check the
   cap *before* instantiating.
2. `model.steps` auto-increments — don't add your own tick counter.
3. The `seed=` kwarg to `Model.__init__` raises a FutureWarning saying to
   use `rng=` instead. Functional today; will need updating.

## Speed

200 seeds × 150 ticks × 2 regimes takes about 4 minutes on a laptop-class
CPU. Hot spot is the per-tick agent loop. If we want v0.2 to sweep over many
parameter combinations, profile `YeastAgent.step` and consider vectorising
the lethal check.

## What the figures should look like (so you notice regressions)

- fig2 (outcome distribution): clearly bimodal for both regimes — a tall bar
  near zero (extinction) and a tall bar near the carrying-capacity mass
  (~3000 biomass). Variable should have a much heavier right peak.
- fig3 (extinction bars): constant in the 0.85–0.95 band, variable in the
  0.50–0.70 band. If constant drops below 0.7 the toxin scale is too weak;
  if variable climbs above 0.8 hormesis is broken.
- fig4 (defense buildup): constant flat at 0. Variable rises to ~0.8 by
  tick 40, then drops post-swan to ~0.4. If constant is non-zero you have
  a stress-score bug.
