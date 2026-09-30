"""Generate PLACEHOLDER data so the app runs offline before real data is downloaded.

!! This is synthetic. Never present model scores trained on it as real results.
Run:  python scripts/make_synthetic_data.py
Outputs: data/historical_data.csv, data/cached_live_data.csv, data/demo_scenarios.csv
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.data_loader import LOCATIONS  # noqa: E402

rng = np.random.default_rng(42)
BASE = {"Indirapuram": 95, "Vasundhara": 90, "Raj Nagar": 85, "Loni": 140,
        "Sahibabad": 120, "Kaushambi": 100, "Noida Sector 62": 92, "Muradnagar (KIET)": 80}


def simulate(name, start, hours):
    t = pd.date_range(start, periods=hours, freq="h")
    hr = t.hour.values
    n = len(t)
    # weather: wind low at night, humidity high at night
    wind = np.clip(8 + 6 * np.sin((hr - 9) / 24 * 2 * np.pi) + rng.normal(0, 2.5, n), 0.5, 40)
    hum = np.clip(65 - 20 * np.sin((hr - 9) / 24 * 2 * np.pi) + rng.normal(0, 6, n), 20, 98)
    temp = 20 + 8 * np.sin((hr - 9) / 24 * 2 * np.pi) + rng.normal(0, 1, n)
    wdir = (rng.normal(300, 40, n)) % 360
    # slow regional episodes (multi-day smog) + AR(1) noise
    episode = np.zeros(n)
    for _ in range(max(1, hours // 200)):
        c = rng.integers(0, n); w = rng.integers(24, 90)
        episode += 70 * np.exp(-0.5 * ((np.arange(n) - c) / w) ** 2)
    ar = np.zeros(n)
    for i in range(1, n):
        ar[i] = 0.92 * ar[i - 1] + rng.normal(0, 5)
    traffic = 25 * (np.exp(-0.5 * ((hr - 9) / 2) ** 2) + 1.3 * np.exp(-0.5 * ((hr - 19) / 2.2) ** 2))
    pm25 = (BASE[name] * 0.55 + episode + traffic + ar) * (1 + 0.8 * (hum - 60) / 100) \
        * (1.4 - 0.025 * np.minimum(wind, 20))
    pm25 = np.clip(pm25 * 0.5, 5, 450)   # calibrated to NCR-like autumn levels
    df = pd.DataFrame({
        "time": t, "location": name,
        "lat": LOCATIONS[name]["lat"], "lon": LOCATIONS[name]["lon"],
        "pm25": pm25, "pm10": pm25 * rng.uniform(1.6, 2.1, n),
        "no2": np.clip(25 + 0.25 * pm25 + rng.normal(0, 6, n), 5, 300),
        "so2": np.clip(10 + 0.05 * pm25 + rng.normal(0, 3, n), 1, 100),
        "co": np.clip(0.5 + 0.006 * pm25 + rng.normal(0, 0.15, n), 0.1, 8),
        "o3": np.clip(40 + 25 * np.sin((hr - 9) / 24 * 2 * np.pi) + rng.normal(0, 8, n), 2, 200),
        "temp": temp, "humidity": hum, "wind": wind, "wind_dir": wdir,
    })
    return df


# 1) historical: ~90 days hourly
hist = pd.concat([simulate(n, "2026-06-30 00:00", 24 * 90) for n in LOCATIONS], ignore_index=True)
num = hist.select_dtypes("number").columns
hist[num] = hist[num].round(3)
(ROOT / "data").mkdir(exist_ok=True)
hist.to_csv(ROOT / "data/historical_data.csv", index=False)

# 2) cached "live" data: most recent 72 h of the history (stand-in until you fetch real data)
last = hist["time"].max()
hist[hist["time"] > last - pd.Timedelta(hours=72)].to_csv(ROOT / "data/cached_live_data.csv", index=False)

# 3) demo scenarios: 72 h each, hand-shaped
def scenario(kind):
    frames = []
    for name in LOCATIONS:
        d = simulate(name, "2026-10-05 00:00", 72)
        h = np.arange(72)
        if kind == "normal":
            f = 0.45
        elif kind == "moderate_to_poor":     # builds through the last 12 h
            f = 0.85 + 0.8 / (1 + np.exp(-(h - 60) / 4))
            d["wind"] = np.where(h > 58, 2.0, d["wind"]); d["humidity"] = np.where(h > 58, 85, d["humidity"])
        else:                                 # severe event
            f = 1.0 + 3.2 / (1 + np.exp(-(h - 56) / 5))
            d["wind"] = np.where(h > 54, 1.0, d["wind"]); d["humidity"] = np.where(h > 54, 90, d["humidity"])
        scale = (BASE[name] / 100)
        for c in ("pm25", "pm10"):
            d[c] = d[c] * f * (0.8 + 0.4 * scale)
        d["no2"] = d["no2"] * (0.6 + 0.4 * np.asarray(f)); d["co"] = d["co"] * (0.7 + 0.3 * np.asarray(f))
        d["scenario"] = kind
        frames.append(d)
    return pd.concat(frames, ignore_index=True)

demo = pd.concat([scenario(k) for k in ("normal", "moderate_to_poor", "severe")], ignore_index=True)
demo[num] = demo[num].round(3)
demo.to_csv(ROOT / "data/demo_scenarios.csv", index=False)
(ROOT / "data" / ".real_data").unlink(missing_ok=True)
print("Wrote historical_data.csv, cached_live_data.csv, demo_scenarios.csv (SYNTHETIC)")
