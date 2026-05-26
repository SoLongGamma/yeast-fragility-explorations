# YeastFort — fragility scorer prototype

A Streamlit prototype that wraps the `v0.1/` ABM as a "protocol fragility
scorer." Upload a fed-batch protocol CSV → 80 Monte Carlo simulations
including a fat-tailed contamination event → fragility score (0–100),
three diagnostic subscores, weak-point list.

**Status:** UX sketch. The scoring engine is the `v0.1/` toy ABM, with all
of its [unresolved problems](../../v0.1/docs/self_critique.md). This is not
a tool to make protocol decisions with.

## Why this exists

To demonstrate what a productized version of the underlying idea *could*
look like, with a working scoring engine behind it. Three axes were planned:

1. **Fragility Scorer** (built) — diagnose.
2. **Protocol Optimizer** (not built) — recommend pulsed-feed and
   heat-shock schedules that improve the score.
3. **Reproducibility Predictor** (not built) — simulate the run-to-run
   distribution under realistic lab noise.

Only axis 1 is implemented.

## Run it locally

```bash
pip install -r requirements.txt
streamlit run app/app.py
```

Two example protocols are bundled in `examples/` for comparison.

## Protocol CSV format

| column        | meaning                                  |
|---------------|------------------------------------------|
| `tick`        | timestep index (0, 1, 2, …)              |
| `temperature` | °C                                       |
| `pH`          |                                          |
| `glucose_feed`| relative units; same scale as your reactor schedule |

A row defines the conditions from its tick until the next row.

## What the scores mean

- **Overall fragility (lower is better).** Weighted combination of the three
  subscores. 0 = bulletproof; 100 = collapses on any disturbance.
- **Shock survival.** Fraction of Monte Carlo runs that survived the
  contamination event.
- **Reproducibility.** Inverse coefficient-of-variation among surviving
  runs, penalized by the share of runs that died.
- **Recovery.** Of runs that took a shock, how many recovered to ≥50% of
  the pre-shock population.

These scores are derived from a toy model. They are not predictions about
your actual lab.
