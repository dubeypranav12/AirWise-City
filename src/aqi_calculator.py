"""Indian National AQI (CPCB) calculation.

NOTE: CPCB defines PM/NO2/SO2 on 24-h averages and CO/O3 on 8-h averages.
AirWise computes an *instantaneous hourly estimate* from hourly readings so the
dashboard can react quickly. Say this openly in your pitch/README.
Units: PM2.5, PM10, NO2, SO2, O3 in ug/m3; CO in mg/m3.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

# Upper concentration limit of each of the six CPCB bands (last one is open-ended,
# we cap it so the 401-500 band interpolates sensibly).
BAND_TOPS = {
    "pm25": [30, 60, 90, 120, 250, 380],
    "pm10": [50, 100, 250, 350, 430, 600],
    "no2":  [40, 80, 180, 280, 400, 560],
    "so2":  [40, 80, 380, 800, 1600, 2400],
    "co":   [1.0, 2.0, 10, 17, 34, 50],
    "o3":   [50, 100, 168, 208, 748, 1000],
}
INDEX_TOPS = [50, 100, 200, 300, 400, 500]

CATEGORIES = [
    (50, "Good", "#2e9e4f"),
    (100, "Satisfactory", "#d4c21a"),
    (200, "Moderate", "#f08a1c"),
    (300, "Poor", "#e03b2f"),
    (400, "Very Poor", "#8e2bb0"),
    (10_000, "Severe", "#7a0f1c"),
]
POLLUTANTS = list(BAND_TOPS.keys())
POLLUTANT_LABELS = {"pm25": "PM2.5", "pm10": "PM10", "no2": "NO\u2082",
                    "so2": "SO\u2082", "co": "CO", "o3": "Ozone"}


def sub_index(pollutant: str, conc) -> float:
    """CPCB sub-index by linear interpolation inside the band. NaN-safe."""
    if conc is None or pd.isna(conc) or conc < 0:
        return np.nan
    c_tops = [0.0] + list(BAND_TOPS[pollutant])
    i_tops = [0.0] + INDEX_TOPS
    if conc >= c_tops[-1]:
        return 500.0
    return float(np.interp(conc, c_tops, i_tops))


def compute_aqi(values: dict):
    """Return (AQI, dominant_pollutant) from a dict of pollutant concentrations."""
    subs = {p: sub_index(p, values.get(p)) for p in POLLUTANTS}
    subs = {p: s for p, s in subs.items() if not np.isnan(s)}
    if not subs:
        return np.nan, None
    dom = max(subs, key=subs.get)
    return float(round(min(subs[dom], 500))), dom


def add_aqi_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add `aqi` and `dominant` columns; tolerates missing pollutant columns/values."""
    out = df.copy()
    subs = pd.DataFrame({p: out[p].apply(lambda v, p=p: sub_index(p, v))
                         for p in POLLUTANTS if p in out.columns})
    out["aqi"] = subs.max(axis=1, skipna=True).round().clip(upper=500)
    out["dominant"] = subs.idxmax(axis=1, skipna=True)
    return out


def category(aqi) -> str:
    if aqi is None or pd.isna(aqi):
        return "Unknown"
    for upper, name, _ in CATEGORIES:
        if aqi <= upper:
            return name
    return "Severe"


def colour(aqi) -> str:
    if aqi is None or pd.isna(aqi):
        return "#888888"
    for upper, _, hexcol in CATEGORIES:
        if aqi <= upper:
            return hexcol
    return CATEGORIES[-1][2]


def rgb(aqi) -> list:
    h = colour(aqi).lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]
