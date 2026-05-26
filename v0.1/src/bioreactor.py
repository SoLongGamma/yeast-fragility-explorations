"""
BioreactorModel — Mesa 3.x model wrapping yeast agents + environment.

Tracks:
  - alive population
  - total biomass (proxy for product titer in v0.1; v0.3 will split product)
  - mean defense capital (proxy for "primedness")
  - environment trace
"""

from __future__ import annotations
import numpy as np
from mesa import Model
from mesa.datacollection import DataCollector

from yeast_agent import YeastAgent
from environment import make_environment


class BioreactorModel(Model):

    def __init__(
        self,
        env_kind: str = "constant",
        n_init: int = 50,
        carrying_capacity: int = 2000,
        glucose_pool: float = 5.0,    # g/L equivalent, refreshed by feed
        feed_per_tick: float = 0.6,   # mean feed rate; matched across regimes
        black_swan: bool = True,
        seed: int | None = None,
    ):
        super().__init__(seed=seed)
        self.carrying_capacity = carrying_capacity
        self.glucose = glucose_pool
        self.feed_per_tick = feed_per_tick
        self.env = make_environment(env_kind, self.random_np_generator(),
                                    black_swan=black_swan)
        self._env_snapshot: dict | None = None
        self._alive_count = 0

        # Seed the population
        for _ in range(n_init):
            YeastAgent(self)  # auto-registers via Mesa 3.x Agent.__init__

        self.datacollector = DataCollector(
            model_reporters={
                "alive": lambda m: sum(1 for a in m.agents if a.alive),
                "biomass": lambda m: sum(a.biomass for a in m.agents if a.alive),
                "mean_defense": lambda m: (
                    float(np.mean([a.defense for a in m.agents if a.alive]))
                    if any(a.alive for a in m.agents) else 0.0
                ),
                "temperature": lambda m: m._env_snapshot["temperature"]
                    if m._env_snapshot else 0.0,
                "glucose_env": lambda m: m._env_snapshot["glucose"]
                    if m._env_snapshot else 0.0,
                "toxin": lambda m: m._env_snapshot["toxin"]
                    if m._env_snapshot else 0.0,
            },
        )

    # ---- helpers ----

    def random_np_generator(self) -> np.random.Generator:
        """Numpy RNG seeded coherently with Mesa's stdlib RNG."""
        seed = self.random.randrange(0, 2**31 - 1)
        return np.random.default_rng(seed)

    def current_environment(self) -> dict:
        return self._env_snapshot

    def consume_glucose(self, amount: float) -> None:
        self.glucose = max(0.0, self.glucose - amount)

    def can_add_daughter(self) -> bool:
        """Density-dependent reproduction gate. Cheap O(1) count."""
        return self._alive_count < self.carrying_capacity

    def _refresh_alive_count(self) -> None:
        self._alive_count = sum(1 for a in self.agents if a.alive)

    # ---- main loop ----

    def step(self):
        # 1) Refresh environment for this tick. The Environment object
        #    decides what the cells experience; the model just adds feed.
        tick = self.steps  # Mesa 3.x auto-increments self.steps
        self._env_snapshot = self.env.sample(tick)
        # Glucose pool tracks env's "glucose" reading for cells to consume —
        # we let cells deplete it and the env's next sample resets the offered
        # value, simulating an externally controlled feed.
        self.glucose = self._env_snapshot["glucose"]

        # 2) Agents act in random order
        self._refresh_alive_count()
        self.agents.shuffle_do("step")

        # 2b) Garbage-collect dead cells so the agents list doesn't bloat.
        # In a real reactor dead cells lyse and are diluted out; in v0.1 we
        # just drop them. Their last-tick contribution was already collected.
        for a in list(self.agents):
            if not a.alive:
                a.remove()

        self._refresh_alive_count()

        # 3) Collect
        self.datacollector.collect(self)

    def run(self, n_ticks: int) -> "pandas.DataFrame":
        for _ in range(n_ticks):
            self.step()
        return self.datacollector.get_model_vars_dataframe()
