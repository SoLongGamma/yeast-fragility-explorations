"""
Loader / validator / converter for fermentation_run.schema.json files.

Workflow:
    raw_json = load_run("data/sources/kim2024_pH55.json")
    issues = validate_run(raw_json)
    abm_schedule = to_abm_protocol(raw_json, tick_per_hour=2)
    -> abm_schedule is a DataFrame that the ABM environment can consume.

This is the bridge between *real-world data* (in many shapes) and the
*ABM input format* (tick, temperature, pH, glucose_feed).
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd


SCHEMA_PATH = Path(__file__).parent.parent / "schema" / "fermentation_run.schema.json"


def load_run(path: str | Path) -> dict[str, Any]:
    """Load a JSON file into a dict."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_run(run: dict[str, Any], strict: bool = False) -> list[str]:
    """
    Validate a run dict against the schema (best-effort, no jsonschema
    dependency — we do the most useful checks by hand).

    Returns a list of issues. Empty list = passes.

    If strict=True, missing optional but high-value fields also become issues.
    """
    issues: list[str] = []

    # Required top-level keys
    for key in ("run_id", "strain", "conditions", "time_series", "source"):
        if key not in run:
            issues.append(f"missing required field: {key}")

    # Strain checks
    strain = run.get("strain", {})
    if not strain.get("species"):
        issues.append("strain.species is empty")
    if not strain.get("strain_id"):
        issues.append("strain.strain_id is empty")

    # Time-series internal consistency
    ts = run.get("time_series", {})
    time_h = ts.get("time_h")
    if not time_h:
        issues.append("time_series.time_h is empty or missing")
    else:
        n = len(time_h)
        for key, arr in ts.items():
            if key == "time_h" or key == "byproducts":
                continue
            if isinstance(arr, list) and len(arr) != n:
                issues.append(
                    f"time_series.{key} has length {len(arr)} "
                    f"but time_h has length {n}"
                )
        if any(b is None for b in (ts.get("biomass_g_per_L_DCW") or [None])):
            if "biomass_OD600" not in ts:
                issues.append("no biomass measurement: need DCW or OD600")

    # Source license
    src = run.get("source", {})
    if not src.get("license"):
        issues.append("source.license is empty (downstream gating depends on it)")

    if strict:
        cond = run.get("conditions", {})
        if cond.get("initial_glucose_g_per_L") is None:
            issues.append("[strict] initial_glucose_g_per_L missing")
        if cond.get("reactor_volume_L") is None:
            issues.append("[strict] reactor_volume_L missing")

    return issues


def to_abm_protocol(run: dict[str, Any], ticks_per_hour: float = 1.0
                    ) -> pd.DataFrame:
    """
    Convert a real fermentation run into the (tick, temperature, pH,
    glucose_feed) DataFrame the v0.1 ABM consumes.

    Parameters
    ----------
    ticks_per_hour
        ABM time-step resolution. The v0.1 ABM uses dimensionless "ticks";
        for real-world data we choose how many ticks ≈ 1 real hour.

    Notes
    -----
    - When the run's pH / temperature are constant (provided as scalar in
      conditions), we broadcast them.
    - feed_rate_mL_per_h is converted into the ABM's `glucose_feed` column
      using the feed solution's glucose concentration. We do NOT attempt
      to model reactor volume changes; this is a screening proxy.
    """
    ts = run["time_series"]
    cond = run["conditions"]
    time_h = np.asarray(ts["time_h"], dtype=float)

    if len(time_h) == 0:
        raise ValueError("Empty time_series.time_h")

    # Generate ABM tick grid (uniform), then interpolate the real series onto it.
    duration_h = time_h[-1] - time_h[0]
    n_ticks = max(int(np.ceil(duration_h * ticks_per_hour)) + 1, 2)
    tick_to_hour = np.linspace(time_h[0], time_h[-1], n_ticks)

    def _interp(field: str, default: float | None) -> np.ndarray:
        arr = ts.get(field)
        if arr is None or all(v is None for v in arr):
            if default is None:
                raise ValueError(f"required time_series field missing: {field}")
            return np.full(n_ticks, default)
        # Replace None with NaN, then interpolate over NaN gaps
        clean = np.array([np.nan if v is None else v for v in arr], dtype=float)
        # Linear interpolation onto tick grid; fill NaNs by linear interp first
        if np.isnan(clean).any():
            mask = ~np.isnan(clean)
            if mask.sum() < 2:
                if default is not None:
                    return np.full(n_ticks, default)
                raise ValueError(f"not enough valid points in {field}")
            clean = np.interp(time_h, time_h[mask], clean[mask])
        return np.interp(tick_to_hour, time_h, clean)

    # Temperature
    temp_scalar = cond.get("temperature_C")
    if isinstance(temp_scalar, (int, float)):
        temperature = np.full(n_ticks, float(temp_scalar))
    else:
        temperature = _interp("temperature_C", default=30.0)

    # pH
    pH_scalar = cond.get("pH_setpoint")
    if isinstance(pH_scalar, (int, float)):
        pH = np.full(n_ticks, float(pH_scalar))
    else:
        pH = _interp("pH", default=5.0)

    # Glucose feed: prefer measured glucose concentration in reactor;
    # fall back to feed_rate × feed_solution glucose if not available.
    glucose_in_reactor = ts.get("glucose_g_per_L")
    if glucose_in_reactor and any(v is not None for v in glucose_in_reactor):
        glucose_feed = _interp("glucose_g_per_L", default=5.0)
    else:
        # Derive an approximate per-tick glucose availability from the
        # feed pump rate. This is a *very rough* proxy and we mark it.
        feed_solution = cond.get("feed_solution_composition") or {}
        feed_glu_conc = feed_solution.get("glucose_g_per_L", 350.0)
        feed_rate = _interp("feed_rate_mL_per_h", default=0.0)
        reactor_vol_L = cond.get("reactor_volume_L") or 1.0
        # Approximate added glucose concentration per hour:
        glucose_feed = feed_rate * feed_glu_conc / 1000.0 / reactor_vol_L

    return pd.DataFrame({
        "tick": np.arange(n_ticks),
        "tick_to_hour": tick_to_hour,
        "temperature": temperature,
        "pH": pH,
        "glucose_feed": glucose_feed,
    })


def to_observed_trajectory(run: dict[str, Any]) -> pd.DataFrame:
    """
    Extract the *observed* biomass + product trajectory from the run, for
    comparison against an ABM simulation. Used by calibration code.
    """
    ts = run["time_series"]
    time_h = np.asarray(ts["time_h"], dtype=float)
    out = {"time_h": time_h}
    biomass = ts.get("biomass_g_per_L_DCW")
    if biomass:
        out["biomass_g_per_L"] = np.array(
            [np.nan if v is None else v for v in biomass], dtype=float
        )
    product = ts.get("product_concentration")
    if product:
        out["product"] = np.array(
            [np.nan if v is None else v for v in product], dtype=float
        )
    return pd.DataFrame(out)


def summarize_dataset(json_files: list[Path]) -> pd.DataFrame:
    """Quick one-row-per-run summary for browsing a dataset directory."""
    rows = []
    for path in json_files:
        try:
            run = load_run(path)
            rows.append({
                "file": path.name,
                "run_id": run.get("run_id", ""),
                "species": run.get("strain", {}).get("species", ""),
                "strain_id": run.get("strain", {}).get("strain_id", ""),
                "product": (run.get("target_product") or {}).get("name", ""),
                "duration_h": (run.get("outcome_summary") or {}).get(
                    "total_duration_h"
                ),
                "license": run.get("source", {}).get("license", ""),
                "issues": "; ".join(validate_run(run)),
            })
        except Exception as e:
            rows.append({
                "file": path.name,
                "run_id": "(load failed)",
                "issues": str(e),
            })
    return pd.DataFrame(rows)
