# Yeast Fed-Batch MVP

Minimal single-screen app for *S. cerevisiae* fed-batch fermentation.
Enter current bioreactor measurements; the app suggests a feed rate and
DO setpoint for the next hour.

## What this is

- A research/exploratory tool for small labs and students.
- A 5-state Monod ODE model with literature-average parameters.
- A grid search over (feed_rate, DO_setpoint) that picks the
  combination predicted to maximize a chosen objective.
- Open source, browser-local. No data is sent anywhere.

## What this is *not*

- Not a GMP-validated tool. Do not use for production decisions.
- Not strain-specific. Parameters are population averages.
- Not a substitute for an experienced bioprocess engineer.
- Not a real-time controller — it gives one recommendation per call.

## How to run

### Locally (closed/air-gapped)

```bash
pip install -r requirements.txt
streamlit run app.py
```

Opens in your browser at `http://localhost:8501`. No network needed
after install.

### Streamlit Cloud (demo, not for sensitive data)

Fork the parent repo, point Streamlit Cloud at `app.py`, and deploy.

## Model

State variables:
- `X` — biomass (g/L)
- `S` — residual glucose (g/L)
- `E` — ethanol (g/L)
- `DO` — dissolved oxygen (%)
- `V` — reactor volume (L)

Manipulated variables (what the app recommends):
- `feed_rate` — substrate feed [g glucose / L / hr]
- `DO_setpoint` — target dissolved oxygen [%]

Dynamics (`model.py`):
- Monod kinetics on glucose, dual substrate with oxygen.
- Crabtree effect: ethanol forms when specific glucose uptake
  exceeds a threshold.
- Volume increases via feed.

## What's intentionally left out (for now)

The parent project (`yeast-fragility-explorations`) explores
antifragility, Spitznagel-style insurance bets, ESC control, and
ecYeast8 dFBA. This MVP includes *none of that*. It exists so the
core recommendation loop is shippable and testable before adding
those layers.

See `docs/decisions.md` in the parent repo for the rationale.

## License

MIT, same as parent repo.
