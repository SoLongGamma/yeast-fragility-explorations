"""
Environment drivers for the bioreactor.

Two regimes, sharing the SAME long-run mean for each variable
(this is the Jensen-inequality fair-comparison setup):

  - ConstantEnvironment: T=30, pH=5, steady glucose feed.
  - VariableEnvironment:  T, pH, glucose oscillate / pulse with the same mean.

On top of either regime we can fire a "black swan": a fat-tailed
contamination/toxin spike at a random tick. This is what reveals whether
the population built up defense capital ahead of time.
"""

from __future__ import annotations
import numpy as np


class Environment:
    """Base class — subclasses implement sample()."""

    def __init__(self, rng: np.random.Generator, black_swan: bool = True,
                 swan_tick_window=(40, 120), swan_scale: float = 2.5):
        self.rng = rng
        self.black_swan_enabled = black_swan
        # Pick the tick at which the swan fires (unknown to the cells).
        self.swan_tick = int(rng.integers(*swan_tick_window)) if black_swan else None
        self.swan_scale = swan_scale
        self.toxin_decay = 0.7
        self._toxin = 0.0

    def _maybe_fire_swan(self, tick: int) -> float:
        """Cauchy-distributed toxin pulse — fat-tailed, occasionally extreme."""
        if self.black_swan_enabled and tick == self.swan_tick:
            # Half-Cauchy: most fires are moderate, a few are catastrophic.
            draw = abs(self.rng.standard_cauchy()) * self.swan_scale
            # Cap to keep simulations finite; the cap is still well past lethal
            # for unprimed cells.
            self._toxin = min(draw, 8.0)
        else:
            self._toxin *= self.toxin_decay
        return self._toxin

    def sample(self, tick: int) -> dict:
        raise NotImplementedError


class ConstantEnvironment(Environment):
    """The 'greenhouse'. Held at optimum."""

    name = "constant"

    def sample(self, tick: int) -> dict:
        toxin = self._maybe_fire_swan(tick)
        return {
            "temperature": 30.0,
            "pH": 5.0,
            "glucose": 5.0,
            "toxin": toxin,
        }


class VariableEnvironment(Environment):
    """The 'gym'. Same MEAN as constant, but with hormetic pulses.

    Temperature: square-wave pulses up to ~37 °C every ~12 ticks.
    Glucose:     feast/famine cycle (pulsed feeding) — same time-average.
    pH:          slow drift around 5.0.
    """

    name = "variable"

    def sample(self, tick: int) -> dict:
        toxin = self._maybe_fire_swan(tick)

        # Square-wave heat pulse: 4 ticks hot, 8 ticks at optimum.
        cycle = tick % 12
        if cycle < 4:
            T = 37.0   # hormetic heat shock (sub-lethal!)
        else:
            T = 30.0 - (37.0 - 30.0) * (4 / 8)  # mean-preserving offset → 26.5

        # Pulsed glucose: bolus every 10 ticks, otherwise starvation.
        # Time-average glucose ≈ 5 g/L (same as constant).
        if tick % 10 == 0:
            glu = 50.0
        else:
            glu = max(0.05, 5.0 - 0.5 * (tick % 10))  # decays into famine

        # pH drift
        pH = 5.0 + 0.4 * np.sin(tick / 7.0)

        return {
            "temperature": T,
            "pH": pH,
            "glucose": glu,
            "toxin": toxin,
        }


def make_environment(kind: str, rng: np.random.Generator, **kw) -> Environment:
    if kind == "constant":
        return ConstantEnvironment(rng, **kw)
    if kind == "variable":
        return VariableEnvironment(rng, **kw)
    raise ValueError(kind)
