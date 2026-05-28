# yeast-fragility-explorations

**🧫 YeastFort scorer (diagnose):** https://yeast-fragility-explorations-cpcqreadyojn3gnsvqmdyc.streamlit.app/
**🧪 Recommender (suggest schedules):** https://[recommender-url].streamlit.app/

Explorations of fragility, hormesis, and reproducibility in
*S. cerevisiae* fermentation — by way of agent-based simulation.

**Status**: exploratory / work in progress.
Not validated against wet-lab data. Treat this as a public notebook, not a tool.

---

## Origin and attribution

This repository is unusual in one respect that I want to be upfront about:

**I did not write the code or the prose myself.** I provided the ideas,
the framing, the philosophical orientation (Taleb's antifragility, Jensen's
inequality, hormesis applied to bioreactors), and the back-and-forth
critical questioning. The code, the simulations, and most of the writing
were produced by Anthropic's Claude over a series of conversations,
following my direction.

I think it's important to say this for two reasons. First, it would be
dishonest to present this as something I personally engineered. Second,
I think the *interesting part* of this project is actually the ideas and
the iterative refinement process — and I want that to be visible.

The full conversation that produced this repository (in **Korean**) is
linked here:

> 👉 [Claude conversation transcript](https://claude.ai/share/b3322610-47cf-4ba2-92c2-a658fb157bec)

If you read Korean, the conversation is more informative than the code,
because it includes the hostile self-critique step where I explicitly
asked Claude to attack the model and find what was rigged. That critique
is preserved in [`v0.1/docs/self_critique.md`](v0.1/docs/self_critique.md).

---

## What's in here

- [`v0.1/`](v0.1/) — A toy ABM that asks whether *intermittent stress*
  in a fed-batch protocol can act as hormetic priming and improve
  reproducibility under fat-tailed disturbances. **The model is mostly
  an illustration of the hypothesis, not evidence for it.** See
  [`v0.1/docs/self_critique.md`](v0.1/docs/self_critique.md) for what's
  wrong with it.

- [`product/yeastfort/`](product/yeastfort/) — A Streamlit prototype that
  wraps the ABM as a "protocol fragility scorer." Demonstrates what a
  productized version *could* look like. Same caveats apply.

- [`docs/roadmap.md`](docs/roadmap.md) — Three plausible paths forward
  if real wet-lab data became available.

- [`docs/what_this_is_not.md`](docs/what_this_is_not.md) — Explicit
  list of things this project does *not* do or claim.

- [`data/`](data/) — Universal intake schema for fermentation run data,
  with one digitized example. Designed so any new dataset (from a paper,
  a lab, or the user) plugs into the same pipeline. See
  [`data/README.md`](data/README.md).

---

## What this is not

- **Not a validated model.** Parameters are order-of-magnitude guesses.
- **Not a publishable result.** Several pre-registered ablation studies
  remain undone (see `self_critique.md`).
- **Not a product.** The Streamlit app is a UX sketch, not a tool you
  should make decisions with.

It is one person's exploration of a question they find interesting:

> *Can intermittent stress make a yeast culture more reproducible?*

The toy answer is "maybe, and here's how it could work in principle."
The real answer requires wet-lab work this project has not done.

---

## Quick look

The headline finding from `v0.1` — with the caveats above — is that
under matched mean conditions and a fat-tailed contamination event, a
"variable" protocol survives more often than a "constant" protocol:

| metric                       | constant   | variable   |
|------------------------------|------------|------------|
| extinction rate (200 seeds)  | **93.5%**  | **60.5%**  |
| mean defense capital at end  | 0.00       | **0.39**   |

But: the model is constructed in such a way that this result was
substantially predetermined by its structural assumptions. The honest
reading is that v0.1 shows what a hormetic-priming hypothesis *would*
look like in simulation, not that the hypothesis is true.

A swan-timing sweep (`v0.1/results/p0_swan_timing_sweep.png`) shows the
advantage collapses when contamination fires before defense has had time
to build, which is at least directionally honest.

---

## License

MIT. See `LICENSE`.
