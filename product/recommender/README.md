# Feed-schedule recommender (v0.2)

A second Streamlit app that compares common fed-batch feed patterns on the
v0.1 generic *S. cerevisiae* ABM and ranks them by predicted yield.

**Live:** *(deploy URL goes here after Streamlit Cloud setup)*

This is **axis 2** of the planned three-axis product:
1. **YeastFort scorer** (v0.1) — diagnose a given protocol's fragility.
2. **Recommender** (this) — surface a shortlist of promising feed schedules.
3. **Bayesian-optimization loop** (planned) — improve recommendations as
   the user enters real wet-lab results.

## What it does

- Generates ~16 candidate schedules from 5 patterns (constant, linear ramp,
  exponential, pulsed, step-up). All candidates share the same
  time-averaged feed, so the comparison isolates *delivery pattern*, not
  total nutrient.
- Runs Monte Carlo simulations of each candidate, including a fat-tailed
  contamination event.
- Ranks by mean yield and reports downside metrics (p10 yield, extinction
  rate, reliability).
- Downloads the winning schedule as a CSV that the YeastFort fragility
  scorer (axis 1) can ingest directly.

## What it doesn't do

- It does not predict actual reactor yields. Numbers are model-internal.
- It does not know your strain. The ABM is calibrated to nothing.
- It does not replace pilot-scale experiments. The ranking is for narrowing
  the search space from 16 schedules to maybe 3 worth piloting.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app/app.py
```

## Honest interpretation

The Top-5 list is a **shortlist of plausible feed patterns**, ordered by
what the toy model thinks will work. The strongest claim it supports is:
*"if the model's mechanism is approximately right, these patterns are worth
trying before these other ones."* That's a useful narrowing — not a
prediction.
