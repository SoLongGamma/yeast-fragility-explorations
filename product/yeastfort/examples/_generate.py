"""Generate two example protocol CSVs to ship with the app."""

import pandas as pd
import numpy as np
from pathlib import Path

OUT = Path(__file__).parent

ticks = np.arange(150)

# Protocol A: naive "set it and forget it" — constant everything
naive = pd.DataFrame({
    "tick": ticks,
    "temperature": 30.0,
    "pH": 5.0,
    "glucose_feed": 5.0,
})
naive.to_csv(OUT / "protocol_naive_constant.csv", index=False)

# Protocol B: primed — pulsed heat shocks + feast-famine, same MEAN as naive
temp = np.where(ticks % 12 < 4, 37.0, 26.5)  # mean ≈ 30
# Pulsed feed: bolus every 10 ticks, otherwise low.
# Tuned so the time-average matches naive (5.0).
bolus = 35.0
base = 1.67
glu = np.where(ticks % 10 == 0, bolus, base)
pH = 5.0 + 0.4 * np.sin(ticks / 7.0)
primed = pd.DataFrame({
    "tick": ticks,
    "temperature": temp,
    "pH": pH,
    "glucose_feed": glu,
})
primed.to_csv(OUT / "protocol_primed_variable.csv", index=False)

print(f"Wrote {OUT}/protocol_naive_constant.csv")
print(f"Wrote {OUT}/protocol_primed_variable.csv")
print(f"\nNaive mean temp: {naive['temperature'].mean():.2f}")
print(f"Primed mean temp: {primed['temperature'].mean():.2f}")
print(f"Naive mean glu: {naive['glucose_feed'].mean():.2f}")
print(f"Primed mean glu: {primed['glucose_feed'].mean():.2f}")
