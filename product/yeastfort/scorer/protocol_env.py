"""
User-protocol-driven environment.

Reads a protocol DataFrame with columns:
  tick, temperature, pH, glucose_feed

And exposes it to the ABM as if it were the real reactor schedule.
The fat-tailed contamination 'swan' still fires on top of whatever the
user prescribed — that is the whole point of the fragility test.
"""

from __future__ import annotations
import sys
from pathlib import Path

# Make the v0.1 src importable without packaging gymnastics
_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent.parent.parent
V01_SRC = _REPO_ROOT / "v0.1" / "src"
sys.path.insert(0, str(V01_SRC))

import numpy as np
import pandas as pd
from environment import Environment  # base class with swan logic


class ProtocolEnvironment(Environment):
    """A reactor schedule read directly from a user's CSV."""

    name = "user_protocol"

    def __init__(self, schedule: pd.DataFrame, rng: np.random.Generator,
                 black_swan: bool = True, swan_tick_window=(40, 120),
                 swan_scale: float = 2.5):
        super().__init__(rng, black_swan=black_swan,
                         swan_tick_window=swan_tick_window,
                         swan_scale=swan_scale)
        # Normalize: required columns, sorted by tick
        required = {"tick", "temperature", "pH", "glucose_feed"}
        missing = required - set(schedule.columns)
        if missing:
            raise ValueError(f"Protocol missing columns: {missing}")
        self.schedule = schedule.sort_values("tick").reset_index(drop=True)
        self._max_tick = int(self.schedule["tick"].max())

    def _lookup(self, tick: int) -> dict:
        """Hold-last-value lookup: a protocol step persists until the next."""
        # Find the latest row whose tick <= current
        idx = self.schedule["tick"].searchsorted(tick, side="right") - 1
        idx = max(0, min(idx, len(self.schedule) - 1))
        row = self.schedule.iloc[idx]
        return {
            "temperature": float(row["temperature"]),
            "pH": float(row["pH"]),
            "glucose": float(row["glucose_feed"]),
        }

    def sample(self, tick: int) -> dict:
        toxin = self._maybe_fire_swan(tick)
        base = self._lookup(tick)
        base["toxin"] = toxin
        return base


def validate_protocol(df: pd.DataFrame) -> tuple[bool, list[str]]:
    """Sanity-check a user upload. Returns (ok, list_of_complaints)."""
    issues = []
    required = ["tick", "temperature", "pH", "glucose_feed"]
    for col in required:
        if col not in df.columns:
            issues.append(f"Missing required column: '{col}'")
    if issues:
        return False, issues

    if df["tick"].min() < 0:
        issues.append("tick values must be >= 0")
    if (df["temperature"] < 0).any() or (df["temperature"] > 60).any():
        issues.append("temperature looks wrong (outside 0–60 °C)")
    if (df["pH"] < 1).any() or (df["pH"] > 12).any():
        issues.append("pH looks wrong (outside 1–12)")
    if (df["glucose_feed"] < 0).any():
        issues.append("glucose_feed must be >= 0")
    if len(df) < 2:
        issues.append("protocol needs at least 2 rows")

    return len(issues) == 0, issues
