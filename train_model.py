"""Train and evaluate the forecasting models.
    python train_model.py          # full
    python train_model.py --quick  # faster, smaller models
Uses data/historical_data.csv (run scripts/fetch_history.py first for REAL data).
"""
import argparse
from src.data_cleaner import clean
from src.data_loader import load_historical
from src.predictor import train

ap = argparse.ArgumentParser(); ap.add_argument("--quick", action="store_true")
args = ap.parse_args()
report = train(clean(load_historical()), quick=args.quick)
for h, res in report.items():
    print(f"\n=== {h}-hour horizon (test set) ===")
    print(f"{'model':26s}{'MAE':>8s}{'RMSE':>8s}{'cat.acc':>9s}{'PoorRecall':>12s}")
    for name, r in res.items():
        t = r["test"]
        print(f"{name:26s}{t['MAE']:8.1f}{t['RMSE']:8.1f}{t['category_accuracy']:9.2f}{t['poor_recall']:12.2f}")
print("\nSaved models/aqi_model.joblib and models/metrics.json")
