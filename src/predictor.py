"""Training, evaluation and inference for 6/12/24-hour AQI forecasts."""
from __future__ import annotations
import json, math
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error

from .aqi_calculator import add_aqi_columns, category
from .feature_engineering import FEATURES, HORIZONS, build_features

MODELS = Path(__file__).resolve().parent.parent / "models"
MODEL_PATH = MODELS / "aqi_model.joblib"
METRICS_PATH = MODELS / "metrics.json"
POOR = 200  # AQI above this = Poor or worse


def _time_split(df: pd.DataFrame):
    """Chronological 70/15/15 split by timestamp (never shuffle time series)."""
    times = np.sort(df["time"].unique())
    t1, t2 = times[int(len(times) * 0.70)], times[int(len(times) * 0.85)]
    return df[df["time"] < t1], df[(df["time"] >= t1) & (df["time"] < t2)], df[df["time"] >= t2]


def _metrics(y, p):
    y, p = np.asarray(y), np.asarray(p)
    cat_acc = np.mean([category(a) == category(b) for a, b in zip(y, p)])
    danger = y > POOR
    recall = float(np.mean(p[danger] > POOR)) if danger.any() else float("nan")
    return {"MAE": float(mean_absolute_error(y, p)),
            "RMSE": float(math.sqrt(mean_squared_error(y, p))),
            "category_accuracy": float(cat_acc), "poor_recall": recall}


def train(historical: pd.DataFrame, quick: bool = False) -> dict:
    """Train persistence/linear/RF/GB per horizon, pick best on validation MAE."""
    df = build_features(add_aqi_columns(historical), with_targets=True)
    bundle = {"features": FEATURES, "horizons": HORIZONS, "models": {}, "rmse": {}, "chosen": {}}
    report = {}
    for h in HORIZONS:
        tgt = f"target_{h}h"
        d = df.dropna(subset=FEATURES + [tgt])
        tr, va, te = _time_split(d)
        cands = {"Linear Regression": LinearRegression(),
                 "Random Forest": RandomForestRegressor(
                     n_estimators=60 if quick else 150, max_depth=12, min_samples_leaf=3,
                     n_jobs=-1, random_state=0),
                 "Gradient Boosting": GradientBoostingRegressor(
                     n_estimators=100 if quick else 250, max_depth=3, learning_rate=0.05,
                     random_state=0)}
        res = {"Persistence (baseline)": {"val": _metrics(va[tgt], va["aqi"]),
                                           "test": _metrics(te[tgt], te["aqi"])}}
        fitted = {}
        for name, m in cands.items():
            m.fit(tr[FEATURES], tr[tgt]); fitted[name] = m
            res[name] = {"val": _metrics(va[tgt], m.predict(va[FEATURES])),
                         "test": _metrics(te[tgt], m.predict(te[FEATURES]))}
        # "simplest model that beats the baseline": must beat persistence on validation MAE
        base = res["Persistence (baseline)"]["val"]["MAE"]
        beating = {n: res[n]["val"]["MAE"] for n in fitted if res[n]["val"]["MAE"] < base}
        best = min(beating, key=beating.get) if beating else None
        bundle["chosen"][h] = best or "Persistence (baseline)"
        if best:
            bundle["models"][h] = fitted[best]
            bundle["rmse"][h] = res[best]["val"]["RMSE"]
        else:
            bundle["rmse"][h] = base and res["Persistence (baseline)"]["val"]["RMSE"]
        report[h] = res
    MODELS.mkdir(exist_ok=True)
    joblib.dump(bundle, MODEL_PATH, compress=3)
    METRICS_PATH.write_text(json.dumps(report, indent=2))
    return report


def load_bundle():
    try:
        return joblib.load(MODEL_PATH)
    except Exception:
        return None  # model file unavailable -> persistence fallback


def _norm_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def forecast_location(df_loc: pd.DataFrame, bundle="auto") -> dict:
    """Forecast for ONE location's recent history (needs >= 25 hourly rows)."""
    if isinstance(bundle, str):          # "auto" -> load from disk; None -> force fallback
        bundle = load_bundle()
    d = df_loc.sort_values("time")
    feats = build_features(d).iloc[[-1]]
    current = float(feats["aqi"].iloc[0])
    out = {"current": current, "category": category(current), "horizons": {}, "model": "persistence",
           "warning": ""}
    usable = bundle is not None and not feats[FEATURES].isna().any(axis=1).iloc[0]
    if bundle is None:
        out["warning"] = "Model file unavailable - using persistence fallback (forecast = current AQI)."
    elif not usable:
        out["warning"] = "Not enough recent history/values for the model - using persistence fallback."
    for h in HORIZONS:
        model = bundle["models"].get(h) if usable else None
        pred = float(model.predict(feats[FEATURES])[0]) if model is not None else current
        pred = float(np.clip(pred, 0, 500))
        sd = bundle["rmse"].get(h, 40.0) if bundle else 40.0
        out["horizons"][h] = {
            "aqi": round(pred), "category": category(pred),
            "low": round(max(0, pred - 1.28 * sd)), "high": round(min(500, pred + 1.28 * sd)),
            "p_poor": 1 - _norm_cdf((POOR - pred) / max(sd, 1e-6)),
            "time": d["time"].iloc[-1] + pd.Timedelta(hours=h)}
    if bundle and usable:
        out["model"] = bundle["chosen"].get(6, "model")
    out["reasons"] = explain(feats.iloc[0])
    return out


def explain(row) -> list:
    """Plain-language contributing factors. These are statistical signals, NOT proven sources."""
    r = []
    if row.get("pm25_roc3", 0) and row["pm25_roc3"] > 8:
        r.append("PM2.5 increased over the previous three hours")
    if row.get("aqi_roc3", 0) and row["aqi_roc3"] > 20:
        r.append("AQI has been rising quickly")
    if row["wind"] < 6:
        r.append("Wind speed is low, so pollutants are not dispersing")
    if row["humidity"] > 70:
        r.append("High humidity is trapping fine particles")
    hr = int(round((math.atan2(row["hour_sin"], row["hour_cos"]) % (2 * math.pi)) / (2 * math.pi) * 24)) % 24
    if 15 <= hr <= 20:
        r.append("Evening traffic period is approaching")
    elif 6 <= hr <= 9:
        r.append("Morning traffic period is under way")
    if row["aqi"] > row.get("aqi_same_hour_yday", row["aqi"]) + 25:
        r.append("AQI is higher than at the same hour yesterday")
    return r or ["No strong short-term driver detected; conditions look steady"]
