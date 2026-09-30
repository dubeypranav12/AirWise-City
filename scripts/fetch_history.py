"""Download REAL hourly history (up to 92 days) from Open-Meteo for every pilot zone.
Run this on your own machine with internet BEFORE training:
    python scripts/fetch_history.py --days 90
Writes data/historical_data.csv (overwrites the synthetic placeholder).
"""
import argparse, sys
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.data_loader import LOCATIONS, fetch_open_meteo  # noqa: E402

ap = argparse.ArgumentParser(); ap.add_argument("--days", type=int, default=90)
args = ap.parse_args()
frames = []
for name in LOCATIONS:
    print("fetching", name, "...")
    frames.append(fetch_open_meteo(name, past_days=min(args.days, 92), timeout=30))
df = pd.concat(frames, ignore_index=True)
df.to_csv(ROOT / "data/historical_data.csv", index=False)
df[df["time"] > df["time"].max() - pd.Timedelta(hours=72)].to_csv(ROOT / "data/cached_live_data.csv", index=False)
(ROOT / "data" / ".real_data").write_text("real data downloaded")
print("saved", len(df), "rows")
