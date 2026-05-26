# What this is not

A short, blunt list to prevent misreading.

---

## This is not a validated scientific result

No claim in this repository has been tested against wet-lab data. The
simulations match themselves and nothing else. Numbers, percentages,
and effect sizes are illustrative of what the underlying hypothesis
*would* predict, not what was *observed*.

## This is not a digital twin

The agent-based model uses order-of-magnitude parameters for generic
*S. cerevisiae*. It is not calibrated to any specific strain, reactor,
or growth medium. Quantitative comparisons to a particular lab's
results will fail.

## This is not a product

The Streamlit prototype in `product/yeastfort/` is a user-experience
sketch — a demonstration of what a productized version *could* look
like, with a real model behind it. Do not use it to make protocol
decisions in a real lab.

## This is not "AI-driven biology"

No machine learning was performed. No biological model was fit to
biological data. The ABM is a hand-built mechanistic toy. The only AI
involved is the large language model used to write the code and the
prose — and that's a tool, not a research method.

## This is not original biology

The underlying ideas — hormesis, intermittent stress, phenotypic
heterogeneity, pulsed feeding — are well established in microbiology
and bioprocess engineering, including in yeast specifically. The
contribution (such as it is) is the combination with Taleb-style
framing and the explicit Monte Carlo treatment of fat-tailed
disturbances. That combination is not, to my knowledge, common, but it
is not novel science either.

## This is not engineering software

The code prioritizes clarity over performance, has minimal test
coverage, and uses defaults chosen for demo legibility rather than
biological accuracy. It should be read, not deployed.

## This is not my work, exactly

The ideas and direction are mine. The code and prose were produced by
Claude (Anthropic) under my direction. The repository's `README.md`
explains this in more detail and links to the originating
conversation.

---

## What it is

A public notebook documenting one person's exploration of whether
intermittent stress could be deliberately introduced into yeast
fermentation protocols as a strategy to improve reproducibility. The
code is the artifact of the exploration, not the point of it. The
point is to put the idea out where someone better-equipped might
notice it and tell me it is wrong, obvious, already done, or — least
likely but most interesting — worth pursuing further.
