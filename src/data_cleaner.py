"""Cleaning: sort, de-duplicate, fill short gaps per location, drop impossible values."""
import numpy as np
import pandas as pd

NUMERIC = ["pm25", "pm10", "no2", "so2", "co", "o3", "temp", "humidity", "wind", "wind_dir"]
LIMITS = {"pm25": (0, 1000), "pm10": (0, 2000), "no2": (0, 800), "so2": (0, 2000),
          "co": (0, 100), "o3": (0, 1000), "humidity": (0, 100), "wind": (0, 200)}


def clean(df: pd.DataFrame, max_gap_hours: int = 3) -> pd.DataFrame:
    df = df.drop_duplicates(["location", "time"]).sort_values(["location", "time"]).copy()
    for col, (lo, hi) in LIMITS.items():
        if col in df.columns:
            df.loc[(df[col] < lo) | (df[col] > hi), col] = np.nan
    parts = []
    for loc, g in df.groupby("location"):
        g = g.set_index("time").asfreq("h")
        g["location"] = loc
        for c in ("lat", "lon"):
            if c in g.columns:
                g[c] = g[c].ffill().bfill()
        cols = [c for c in NUMERIC if c in g.columns]
        g[cols] = g[cols].interpolate(limit=max_gap_hours, limit_direction="both")
        parts.append(g.reset_index())
    return pd.concat(parts, ignore_index=True)
