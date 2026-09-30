"""Time-series features for AQI forecasting (computed per location, no look-ahead)."""
import numpy as np
import pandas as pd

HORIZONS = [6, 12, 24]
FEATURES = [
    "pm25", "pm10", "no2", "so2", "co", "o3", "temp", "humidity", "wind",
    "wind_sin", "wind_cos", "hour_sin", "hour_cos", "dow", "aqi",
    "aqi_lag1", "aqi_avg3", "aqi_avg6", "aqi_roc3", "pm25_roc3", "aqi_same_hour_yday",
]


def build_features(df: pd.DataFrame, with_targets: bool = False) -> pd.DataFrame:
    """`df` needs time, location and an `aqi` column (see aqi_calculator.add_aqi_columns)."""
    out = []
    for _, g in df.sort_values(["location", "time"]).groupby("location"):
        g = g.copy()
        g["hour_sin"] = np.sin(2 * np.pi * g["time"].dt.hour / 24)
        g["hour_cos"] = np.cos(2 * np.pi * g["time"].dt.hour / 24)
        g["dow"] = g["time"].dt.dayofweek
        rad = np.deg2rad(g["wind_dir"])
        g["wind_sin"], g["wind_cos"] = np.sin(rad), np.cos(rad)
        g["aqi_lag1"] = g["aqi"].shift(1)
        g["aqi_avg3"] = g["aqi"].rolling(3, min_periods=1).mean()
        g["aqi_avg6"] = g["aqi"].rolling(6, min_periods=1).mean()
        g["aqi_roc3"] = g["aqi"] - g["aqi"].shift(3)
        g["pm25_roc3"] = g["pm25"] - g["pm25"].shift(3)
        g["aqi_same_hour_yday"] = g["aqi"].shift(24)
        if with_targets:
            for h in HORIZONS:
                g[f"target_{h}h"] = g["aqi"].shift(-h)
        out.append(g)
    res = pd.concat(out, ignore_index=True)
    return res
