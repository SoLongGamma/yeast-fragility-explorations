# Yeast Fed-Batch v1.1 — Robust Recommender

Differences from v1.0:

1. **6-state ODE** — adds mitochondrial product P (TCA-derived carbon).
2. **Monte Carlo** — every (feed, DO) combination is evaluated under
   ~100 random parameter draws, not just one deterministic simulation.
3. **2× harsh training** — the random parameter draws use 2× the
   realistic σ. The 'Roman training' principle: train under tougher
   conditions than reality so the recommendation has safety margin.
4. **p10 ranking** — the recommendation is the (feed, DO) with the
   highest *worst-10%* yield, not the highest mean yield.
5. **Distribution shown** — UI shows mean, std, p10/p50/p90 instead of
   a single number.

## Why these choices

**Why fed-batch?** Closed reactor with controlled substrate addition.
The standard industrial mode for yeast cultivation. Matches the user's
stated setup (closed vessel, gradual feed).

**Why 6 states (adding P)?** The original 5-state model only tracked
ethanol. For users targeting mitochondrial products (citrate,
succinate, malate, fumarate, 2-oxoglutarate, recombinant proteins
requiring ATP), tracking ethanol alone misses the point. The Crabtree
effect splits glucose between the ethanol branch (cytosol) and the
mitochondrial branch (TCA). Tracking both makes the trade-off
explicit.

**Why 2× σ?** Real lab-to-lab CV in inoculum size, μ_max, and Y_XS
is ~10–15%. Training a recommender at exactly that σ produces a
recommendation that is fragile when the actual batch is at the worse
end of the distribution. Training at 2× σ leaves a margin. The
multiplier is exposed as a slider so the user can choose more or less
conservatism.

**Why p10?** Mean yield is what textbooks optimize. p10 is what an
operator cares about — the worst 10% of batches determines whether a
process is acceptable in practice. A recommendation that maximizes
mean while having a low p10 is a worse practical choice than one with
slightly lower mean and substantially higher p10.

## What this is *not*

- Not GMP-validated.
- Not strain-specific (literature-average parameters).
- Not a real-time controller — one recommendation per call.
- Not a substitute for an experienced bioprocess engineer.

## How to run

Locally (closed/air-gapped):

```bash
pip install -r requirements.txt
streamlit run app_v11.py
```

Opens at `http://localhost:8501`. No network needed after install.

## Performance

A single recommendation runs 24 combinations × 100 trials = 2400
fed-batch simulations. Each simulation is ~0.05 s, so the full
recommendation takes ~2 minutes on a laptop. Lower the `n_trials`
slider for faster iteration.

## Files

```
yeast_mvp_v11/
├── model_v11.py        Fed-batch ODE + Monte Carlo + p10 ranking
├── app_v11.py          Streamlit UI
├── requirements.txt    Deps
└── README.md           This file
```

## License

MIT, same as parent repo.
