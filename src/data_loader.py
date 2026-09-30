"""Data access with three modes: live (Open-Meteo) -> cached CSV -> demo replay.

Every function returns tidy hourly rows with columns:
time, location, lat, lon, pm25, pm10, no2, so2, co (mg/m3), o3,
temp, humidity, wind (km/h), wind_dir
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import requests

from .aqi_calculator import add_aqi_columns

DATA = Path(__file__).resolve().parent.parent / "data"

# Pilot zones: Ghaziabad / Delhi NCR (approximate centre points) and a rough
# population figure used ONLY for the "citizens potentially affected" estimate.
LOCATIONS = {
    "Indirapuram":    {"lat": 28.6460, "lon": 77.3690, "pop": 350_000},
    "Vasundhara":     {"lat": 28.6600, "lon": 77.3700, "pop": 250_000},
    "Raj Nagar":      {"lat": 28.6750, "lon": 77.4400, "pop": 300_000},
    "Loni":           {"lat": 28.7500, "lon": 77.2850, "pop": 520_000},
    "Sahibabad":      {"lat": 28.6800, "lon": 77.3600, "pop": 400_000},
    "Kaushambi":      {"lat": 28.6450, "lon": 77.3200, "pop": 180_000},
    "Noida Sector 62": {"lat": 28.6270, "lon": 77.3650, "pop": 220_000},
    "Muradnagar (KIET)": {"lat": 28.7770, "lon": 77.5090, "pop": 150_000},
}
DEFAULT_LOCATION = "Indirapuram"

AQ_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
WX_URL = "https://api.open-meteo.com/v1/forecast"
AQ_VARS = "pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone"
WX_VARS = "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m"


def fetch_open_meteo(name: str, past_days: int = 3, timeout: int = 10) -> pd.DataFrame:
    """Hourly air quality + weather for one location from Open-Meteo (no API key)."""
    loc = LOCATIONS[name]
    common = {"latitude": loc["lat"], "longitude": loc["lon"],
              "timezone": "Asia/Kolkata", "past_days": past_days, "forecast_days": 1}
    aq = requests.get(AQ_URL, params={**common, "hourly": AQ_VARS}, timeout=timeout)
    wx = requests.get(WX_URL, params={**common, "hourly": WX_VARS}, timeout=timeout)
    aq.raise_for_status(); wx.raise_for_status()
    a = pd.DataFrame(aq.json()["hourly"]); w = pd.DataFrame(wx.json()["hourly"])
    df = a.merge(w, on="time")
    df = df.rename(columns={"pm2_5": "pm25", "nitrogen_dioxide": "no2",
                            "sulphur_dioxide": "so2", "ozone": "o3",
                            "carbon_monoxide": "co", "temperature_2m": "temp",
                            "relative_humidity_2m": "humidity",
                            "wind_speed_10m": "wind", "wind_direction_10m": "wind_dir"})
    df["co"] = df["co"] / 1000.0            # ug/m3 -> mg/m3 (CPCB unit)
    df["time"] = pd.to_datetime(df["time"])
    df["location"] = name; df["lat"] = loc["lat"]; df["lon"] = loc["lon"]
    # keep only observed/analysis hours up to "now"
    now = pd.Timestamp.now(tz="Asia/Kolkata").tz_localize(None)
    return df[df["time"] <= now].reset_index(drop=True)


def fetch_live_all(past_days: int = 3) -> pd.DataFrame:
    frames = [fetch_open_meteo(n, past_days) for n in LOCATIONS]
    return pd.concat(frames, ignore_index=True)


def _read(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["time"])
    return df


def load_cached() -> pd.DataFrame:
    return _read(DATA / "cached_live_data.csv")


def load_demo(scenario: str) -> pd.DataFrame:
    df = _read(DATA / "demo_scenarios.csv")
    return df[df["scenario"] == scenario].drop(columns="scenario").reset_index(drop=True)


def load_historical() -> pd.DataFrame:
    return _read(DATA / "historical_data.csv")


def get_data(mode: str = "Live", scenario: str = "moderate_to_poor"):
    """Return (df_with_aqi, mode_used, message). Falls back Live -> Cached -> Demo."""
    msg = ""
    if mode == "Live":
        try:
            df = fetch_live_all()
            df.to_csv(DATA / "cached_live_data.csv", index=False)   # refresh cache
            return add_aqi_columns(df), "Live", "Live data from Open-Meteo."
        except Exception as exc:                                     # network/API down
            msg = f"Live API unavailable ({type(exc).__name__}); "
            mode = "Cached"
    if mode == "Cached":
        try:
            return add_aqi_columns(load_cached()), "Cached", msg + "Showing last cached data."
        except Exception:
            msg += "No cache found; "
            mode = "Demo"
    return add_aqi_columns(load_demo(scenario)), "Demo", msg + f"Replaying demo scenario '{scenario}'."
