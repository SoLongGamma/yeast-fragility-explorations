"""
Schedule generators for the recommender.

Five patterns commonly used (or proposed) in S. cerevisiae fed-batch:
  1. constant       — flat feed
  2. linear         — linearly increasing feed (DCW often grows linearly mid-fermentation)
  3. exponential    — μ_max-driven; the industrial default for high-density culture
  4. pulsed         — bolus + starvation cycles (the hormesis-friendly pattern)
  5. step_up        — increase feed at fixed milestones (low-tech alternative to exponential)

Each generator returns a pandas DataFrame with columns:
  tick, temperature, pH, glucose_feed

Temperature and pH are held at sensible defaults (30 °C, pH 5) so the
recommender focuses on the *feed-schedule* axis the user actually controls
on most reactors. A future v0.4 can sweep T/pH too.

All schedules share the same TIME-AVERAGED feed (TARGET_MEAN_FEED) so the
recommender compares *delivery patterns*, not "more food vs less food".
That equal-area constraint is what makes the comparison fair.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Iterator
import numpy as np
import pandas as pd


# All candidate schedules deliver the SAME time-averaged glucose feed.
# Changing this number doesn't change rankings, only absolute yields.
TARGET_MEAN_FEED = 5.0   # g/L equivalent (matched to v0.1 conventions)
DEFAULT_TICKS = 150
DEFAULT_TEMP = 30.0
DEFAULT_PH = 5.0


@dataclass
class Candidate:
    """A single feed-schedule candidate."""
    name: str                # e.g. "pulsed_b30_i10"
    pattern: str             # "constant" | "linear" | "exponential" | ...
    params: dict             # human-readable parameter dict
    schedule: pd.DataFrame   # the actual tick-by-tick schedule

    def short_label(self) -> str:
        """One-line UI label."""
        if self.pattern == "constant":
            return "Constant feed (flat baseline)"
        if self.pattern == "linear":
            slope = self.params["slope"]
            direction = "ramp up" if slope > 0 else "ramp down"
            return f"Linear {direction} (slope={slope:+.2f})"
        if self.pattern == "exponential":
            mu = self.params["mu"]
            return f"Exponential (μ={mu:.2f})"
        if self.pattern == "pulsed":
            return (f"Pulsed: bolus={self.params['bolus']:.0f} "
                    f"every {self.params['interval']} ticks")
        if self.pattern == "step_up":
            return f"Step-up at ticks {self.params['steps']}"
        return self.name


def _frame(feed: np.ndarray, ticks: int) -> pd.DataFrame:
    return pd.DataFrame({
        "tick": np.arange(ticks),
        "temperature": np.full(ticks, DEFAULT_TEMP),
        "pH": np.full(ticks, DEFAULT_PH),
        "glucose_feed": feed,
    })


def _rescale_to_target_mean(feed: np.ndarray) -> np.ndarray:
    """Scale a non-negative feed profile so its mean equals TARGET_MEAN_FEED."""
    current = feed.mean()
    if current <= 0:
        return feed
    return feed * (TARGET_MEAN_FEED / current)


# ---------- pattern 1: constant ----------

def gen_constant(ticks: int = DEFAULT_TICKS) -> Iterator[Candidate]:
    """Constant has no hyperparameter — just the baseline."""
    feed = np.full(ticks, TARGET_MEAN_FEED)
    yield Candidate(
        name="constant",
        pattern="constant",
        params={},
        schedule=_frame(feed, ticks),
    )


# ---------- pattern 2: linear ramp ----------

def gen_linear(ticks: int = DEFAULT_TICKS) -> Iterator[Candidate]:
    """Linear ramp; sweep slope sign and magnitude. Mean preserved by rescaling."""
    # Slopes expressed as (end / start) ratio for interpretability.
    # 0.3 = end is 30% of start (decreasing); 3.0 = end is 3x start (increasing)
    for ratio in (0.3, 0.5, 2.0, 3.0):
        # feed(t) = a + b*t, with mean = TARGET_MEAN_FEED
        # end/start = ratio => (a + b*(T-1)) / a = ratio => b = a*(ratio-1)/(T-1)
        T = ticks
        # pick a such that mean = TARGET_MEAN_FEED:
        # mean = a + b*(T-1)/2 = a * (1 + (ratio-1)/2) = a * (ratio+1)/2
        a = TARGET_MEAN_FEED * 2 / (ratio + 1)
        b = a * (ratio - 1) / max(T - 1, 1)
        feed = a + b * np.arange(T)
        feed = np.maximum(feed, 0.01)  # never go negative
        yield Candidate(
            name=f"linear_r{ratio:.1f}",
            pattern="linear",
            params={"end_over_start": ratio, "slope": b},
            schedule=_frame(feed, ticks),
        )


# ---------- pattern 3: exponential ----------

def gen_exponential(ticks: int = DEFAULT_TICKS) -> Iterator[Candidate]:
    """
    Exponential feed: F(t) = F0 * exp(mu * t).
    mu is the target specific growth rate the feed is designed to maintain.
    Industrial default: mu ≈ 0.05–0.15 / hr (here, per-tick proxy).
    """
    for mu in (0.01, 0.02, 0.03, 0.05):
        T = ticks
        # F0 chosen so mean over [0, T) equals TARGET_MEAN_FEED:
        # integral 0..T of F0*exp(mu*t) dt = F0/mu * (exp(mu*T)-1)
        # mean = F0/(mu*T) * (exp(mu*T)-1) = TARGET_MEAN_FEED
        # => F0 = TARGET_MEAN_FEED * mu * T / (exp(mu*T)-1)
        F0 = TARGET_MEAN_FEED * mu * T / (np.exp(mu * T) - 1)
        feed = F0 * np.exp(mu * np.arange(T))
        yield Candidate(
            name=f"exp_mu{mu:.2f}",
            pattern="exponential",
            params={"mu": mu, "F0": F0},
            schedule=_frame(feed, ticks),
        )


# ---------- pattern 4: pulsed (bolus + starvation) ----------

def gen_pulsed(ticks: int = DEFAULT_TICKS) -> Iterator[Candidate]:
    """
    Pulsed feeding: bolus B every I ticks, near-zero baseline otherwise.
    Sweeps the (bolus, interval) grid. Mean preserved by construction.
    """
    base = 0.5  # small trickle between bolus (more realistic than zero)
    for interval in (5, 10, 15, 20):
        # Mean = (base * (interval-1) + bolus) / interval = TARGET_MEAN_FEED
        # => bolus = interval * TARGET_MEAN_FEED - base * (interval - 1)
        bolus = interval * TARGET_MEAN_FEED - base * (interval - 1)
        if bolus < base:
            continue   # degenerate
        feed = np.full(ticks, base)
        feed[::interval] = bolus
        yield Candidate(
            name=f"pulsed_b{bolus:.0f}_i{interval}",
            pattern="pulsed",
            params={"bolus": bolus, "interval": interval, "base": base},
            schedule=_frame(feed, ticks),
        )


# ---------- pattern 5: step-up ----------

def gen_step_up(ticks: int = DEFAULT_TICKS) -> Iterator[Candidate]:
    """
    Two- or three-step ladder: low feed early, higher feed later.
    Useful proxy for "switch to production phase at tick X."
    """
    for n_steps, ratio in (
        (2, 2.0),   # double the feed at midpoint
        (2, 4.0),   # quadruple at midpoint
        (3, 3.0),   # three increasing steps
    ):
        T = ticks
        boundaries = np.linspace(0, T, n_steps + 1, dtype=int)
        # Geometric increase
        levels = ratio ** np.arange(n_steps)
        feed = np.zeros(T)
        for i in range(n_steps):
            feed[boundaries[i]:boundaries[i + 1]] = levels[i]
        feed = _rescale_to_target_mean(feed)
        yield Candidate(
            name=f"step_n{n_steps}_r{ratio:.0f}",
            pattern="step_up",
            params={"n_steps": n_steps, "ratio": ratio,
                    "steps": boundaries[1:-1].tolist()},
            schedule=_frame(feed, ticks),
        )


# ---------- combined ----------

def generate_all(ticks: int = DEFAULT_TICKS) -> list[Candidate]:
    """Return the full candidate list (typically ~15 schedules)."""
    candidates = []
    for gen in (gen_constant, gen_linear, gen_exponential,
                gen_pulsed, gen_step_up):
        candidates.extend(gen(ticks))
    return candidates


if __name__ == "__main__":
    cs = generate_all()
    print(f"Generated {len(cs)} candidate schedules:")
    for c in cs:
        mean = c.schedule["glucose_feed"].mean()
        print(f"  {c.name:25s}  mean_feed={mean:5.2f}  "
              f"[{c.short_label()}]")
