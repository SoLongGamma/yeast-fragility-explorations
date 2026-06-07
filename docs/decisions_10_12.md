# Decisions 10–12 (app phase)

Continues `decisions_summary.md` (decisions 1–9). These cover the
shift from analysis to a shippable tool, and the philosophy pivot that
followed.

---

## Decision 10 — Ship the simplest app first (v1.0 MVP)

After much modeling, build an actual tool. 5-state ODE (X, S, E, DO,
V), Streamlit single screen, grid search over (feed, DO). Deliberately
exclude antifragility, Spitznagel, Monte Carlo — those are layers for
later. The goal is a working recommendation loop.

A unit bug (Crabtree threshold mismatch, ethanol always zero) was
found and fixed — the same class of error as the earlier biomass
blow-up in the lab notebook. Pattern: simulation bugs are usually unit
mismatches, caught by sanity-checking outputs against known ranges.

## Decision 11 — Robust optimization + mitochondrial product (v1.1)

Two additions:

1. **6th state P** — mitochondrial (TCA-derived) product. The original
   model tracked only ethanol; for users targeting citrate, succinate,
   malate, etc., the Crabtree split between cytosolic ethanol and
   mitochondrial product must be explicit.

2. **Robust optimization** ('Roman training' principle): run Monte
   Carlo at 2× realistic σ, rank by p10 (worst-10% yield) rather than
   mean. Train under tougher-than-real conditions so the
   recommendation has safety margin. Inspired by Spitznagel's
   tail-hedging logic but implemented as standard robust optimization.

## Decision 12 — Pivot from "find the optimum" to "avoid the bad" (risk map)

The most important pivot of the app phase. Prompted by recognizing:

- Industrial fermentations run 40–100+ hours; contamination rate is
  ~10% (1 in 10 bioreactors). Avoiding batch failure matters more than
  squeezing out 5% more yield.
- A 5-state model with literature-average parameters cannot reliably
  pinpoint *the optimum*, but it can reliably flag *dangerous regions*.

New philosophy:

| Old (v1.0/v1.1) | New (risk map) |
|---|---|
| "Here's the best (feed, DO)" | "Here are the dangerous (feed, DO) — avoid them" |
| Needs accurate model | Tolerates rough model |
| Optimization | Avoidance / classification |
| Output: a point | Output: a colored safety map |

Implementation:
- Grid of (feed, DO), each cell classified by Monte Carlo failure rate
  (green <10%, caution 10–30%, danger >30%).
- Contamination event included: probability rises with residual
  glucose and with low DO (matches literature — lactic acid bacteria
  favored by leftover sugar and anaerobic conditions).
- Lab-specific: each lab's past batches estimate its own parameter
  distribution, so the risk map is calibrated per lab.

Monte Carlo's role here is natural: measuring "how often does this
(feed, DO) combination fail?" is exactly what Monte Carlo does well.

## Connection to earlier decisions

- The risk map's failure rate is the same quantity as the ABM's
  *culture failure rate* (Phase A heavy, −41 pp). The whole project's
  central metric is now consistent across backends.
- The "avoid the bad" framing fits Decision 8 (event-triggered
  control): the tool is called repeatedly, each call flagging unsafe
  regions for the next interval, not prescribing one global plan.
- Model drift (parameters change over a long fermentation) means the
  tool must be re-called with fresh measurements each interval —
  receding-horizon use, not single-shot.

## Current position (end of app phase)

- v1.0 MVP, v1.1 robust optimizer, risk-map prototype — all working.
- Target user narrowed to graduate-lab 5L bioreactor operators.
- Business model: subscription, with lab-specific calibration stored
  locally (to preserve the "data never leaves" property).

## Still open

- Parameter calibration from real data (currently literature average).
- Contamination probability model (currently a hand-set value, not
  matched to the industrial 10% figure).
- Subscription vs privacy: where calibration data is stored.
- Validation that flagged "danger" regions are actually dangerous.
