"""
YeastAgent: an individual S. cerevisiae cell with hormetic stress response.

The agent has two internal modes:
  - GROWTH: when conditions are calm, invest energy into budding/division.
  - DEFENSE: when stressed, divert energy into heat-shock proteins,
             trehalose, antioxidants. Growth slows but survival robustness
             (the "basin of attraction" width) expands.

Key idea (anti-fragile / hormesis):
  Cells that have *recently experienced* moderate-to-high stress carry
  elevated defense capital. If a black-swan event hits, they survive.
  Cells coddled in a constant-optimum environment have no defense capital
  and die when the same shock arrives.
"""

from __future__ import annotations
import numpy as np
from mesa import Agent


# Reference physiology for S. cerevisiae (rough, order-of-magnitude).
T_OPT = 30.0           # °C, optimum growth temperature
T_LETHAL_HIGH = 42.0   # °C, heat-shock death threshold (unprimed cells)
T_LETHAL_LOW = 5.0     # °C, cold-shock death threshold
PH_OPT = 5.0
GLUCOSE_HALF_SAT = 0.5  # g/L, Monod K_s (rough)
MAX_DEFENSE = 1.0       # cap on defense capital (HSPs, trehalose proxy)


class YeastAgent(Agent):
    """One yeast cell. Mesa 3.x style: no positional unique_id."""

    def __init__(self, model, initial_defense: float = 0.0):
        super().__init__(model)
        self.alive = True
        self.biomass = 1.0                       # arbitrary units
        self.defense = float(initial_defense)    # 0..MAX_DEFENSE
        self.age = 0
        # Hidden individual variability — Talebian "invisible error".
        # Each cell has a slightly different intrinsic robustness.
        # Drawn once at birth; this is what makes ABM > ODE for our question.
        self.intrinsic_robustness = self.random.gauss(1.0, 0.08)
        self.lifetime_stress_dose = 0.0          # for diagnostics

    # ---------- biology ----------

    def _stress_score(self, env) -> float:
        """Map current environment to an instantaneous stress level in [0, ~).

        Bigger = worse. 0 means perfectly optimal.
        """
        T = env["temperature"]
        pH = env["pH"]
        glu = env["glucose"]

        # Thermal stress: quadratic departure from optimum, normalized.
        thermal = ((T - T_OPT) / 8.0) ** 2
        # pH stress
        ph_s = ((pH - PH_OPT) / 1.5) ** 2
        # Starvation stress (low glucose hurts; high glucose is fine here —
        # osmotic stress at very high glucose is a v0.2 refinement).
        starv = max(0.0, 1.0 - glu / (glu + GLUCOSE_HALF_SAT))

        return thermal + ph_s + starv

    def _lethal_check(self, env) -> bool:
        """Hard kill conditions. Defense capital widens the survivable band."""
        T = env["temperature"]
        # Defense pushes the lethal threshold further out — this is
        # literally the "basin of attraction" expansion the user described.
        upper = T_LETHAL_HIGH + 4.0 * self.defense * self.intrinsic_robustness
        lower = T_LETHAL_LOW - 3.0 * self.defense * self.intrinsic_robustness
        if T > upper or T < lower:
            return True
        # Toxin / contamination shock (set by the model when a black-swan fires)
        toxin = env.get("toxin", 0.0)
        survivable_toxin = 0.3 + 0.9 * self.defense * self.intrinsic_robustness
        if toxin > survivable_toxin:
            return True
        return False

    def step(self):
        if not self.alive:
            return

        env = self.model.current_environment()
        self.age += 1

        # 1) Lethal check first (black-swan kills before anything else)
        if self._lethal_check(env):
            self.alive = False
            return

        # 2) Compute sub-lethal stress and update defense capital.
        s = self._stress_score(env)
        self.lifetime_stress_dose += s

        # Hormesis: moderate stress UP-regulates defense; extreme stress
        # damages too fast for adaptation to help on this tick.
        if 0.15 < s < 2.0:
            # adaptive induction
            self.defense = min(MAX_DEFENSE, self.defense + 0.05 * s)
        elif s <= 0.15:
            # coddled — defense decays (the "greenhouse" pathology)
            self.defense = max(0.0, self.defense - 0.02)
        # s >= 2.0: no further induction this tick; survival comes from
        # whatever defense was already stockpiled.

        # 3) Growth: Monod kinetics, paid down by stress and defense cost.
        glu = env["glucose"]
        mu_max = 0.4 * self.intrinsic_robustness   # per tick
        mu = mu_max * glu / (GLUCOSE_HALF_SAT + glu)
        # Stress and defense both reduce realized growth (skin in the game:
        # defense isn't free — that's exactly Taleb's point).
        realized = mu * np.exp(-0.6 * s) * (1.0 - 0.3 * self.defense)
        self.biomass += max(0.0, realized)

        # 4) Consume glucose (model handles the bookkeeping)
        self.model.consume_glucose(realized * 0.5)

        # 5) Budding: split when biomass crosses threshold.
        # Carrying-capacity check happens BEFORE creating the daughter,
        # because Mesa 3.x auto-registers any new Agent into model.agents
        # via Agent.__init__ — we can't un-register cheaply.
        if self.biomass >= 2.0 and self.alive:
            self.biomass = 1.0
            if self.model.can_add_daughter():
                # Daughter inherits ~70% of mother's defense (epigenetic-ish)
                YeastAgent(self.model, initial_defense=0.7 * self.defense)
