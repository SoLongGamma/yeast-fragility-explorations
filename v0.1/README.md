# v0.1 — toy ABM of hormetic priming under fat-tailed disturbance

A small agent-based model where each cell is a yeast carrying:
- a biomass that grows by Monod kinetics on glucose,
- a `defense` scalar that accumulates under sub-lethal stress,
- a hidden `intrinsic_robustness` drawn at birth.

Two environments are compared:
- **constant** — held at 30°C, pH 5, steady glucose
- **variable** — same mean conditions delivered with hormetic pulses
  (square-wave heat shocks, feast-and-famine glucose, sinusoidal pH)

A half-Cauchy "black swan" toxin pulse fires at a random tick in
[40, 120].

## Read this first

→ [`docs/self_critique.md`](docs/self_critique.md) — what's wrong with
this model, what was tested, and what was not.

If you skip this and only look at the figures, you will overestimate
what v0.1 demonstrates.

## Reproduce

```bash
pip install -r ../requirements.txt
cd src
python run_monte_carlo.py --n-seeds 200 --ticks 150
python make_figures.py
python p0_swan_timing_sweep.py --n-seeds 50 --ticks 130
```

Outputs land in `results/`.
