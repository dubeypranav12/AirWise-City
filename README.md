# AirWise City

AI-powered AQI **forecasting, citizen warning and urban-action** platform.
Pilot area: Ghaziabad / Delhi NCR. Software-only (no sensors). Hackathon: Problem Statement 3 - Rising AQI Levels in Modern Urban Cities.

> AirWise City does not just tell people the air is polluted - it predicts when and where pollution will become dangerous, warns vulnerable citizens, and helps authorities choose timely interventions.

## Quick start (5 minutes)

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python scripts/make_synthetic_data.py                   # offline placeholder data (already included)
python train_model.py --quick                           # trains models (already included, trained on synthetic data)
streamlit run app.py
```

In the sidebar choose **Live / Cached / Demo** mode. **Demo -> moderate_to_poor** replays the pollution event used in the pitch.

## Use REAL data (do this today)

```bash
python scripts/fetch_history.py --days 90     # Open-Meteo, no key needed; needs internet
python train_model.py                         # retrain on real data; read the printed table honestly
```

The shipped `models/aqi_model.joblib` and `data/*.csv` are **synthetic placeholders** so the app runs offline.
Never quote scores from them as real results. Retrain on real data before presenting numbers.

## Pages

| Page | What it does |
|---|---|
| `app.py` (City Overview) | Current AQI, category, 6 pollutants, weather, 48 h trend, 6 h forecast banner |
| 1 AQI Forecast | 6/12/24 h forecast, 80% range, P(Poor+), trend chart, plain-language reasons |
| 2 Hotspot Map | Coloured zones (current or 6 h forecast), tooltip + recommended action |
| 3 Health Advisor | Profile-based advice (adult, child, elderly, asthma, outdoor worker, athlete) |
| 4 Authority Console | Risk table, interventions, Telegram alerts + history, CSV report, policy simulator |

## Modes and fallbacks

- **Live**: Open-Meteo Air Quality + Weather APIs (refreshes the cache on success)
- **Cached**: `data/cached_live_data.csv`
- **Demo**: `data/demo_scenarios.csv` (normal / moderate_to_poor / severe)
- Missing pollutant values -> AQI from the remaining pollutants; missing model file -> persistence fallback with a visible warning; Telegram down -> in-app message.

## Modelling

Targets: AQI at +6 / +12 / +24 h. Models: persistence baseline, Linear Regression, Random Forest, Gradient Boosting.
Chronological 70/15/15 split. Metrics: MAE, RMSE, category accuracy, **recall for Poor-or-worse** (safety first).
A model is used only if it beats persistence on validation MAE; otherwise the app falls back to persistence.

## Telegram alerts

1. Talk to `@BotFather` -> `/newbot` -> copy the token. 2. Message your bot, open `https://api.telegram.org/bot<TOKEN>/getUpdates`, copy `chat.id`.
3. Locally: set env vars `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`. On Streamlit Cloud: Settings -> Secrets (see `.streamlit/secrets.toml.example`).

## Deploy

Push to GitHub -> https://share.streamlit.io -> New app -> select repo -> main file `app.py`.

## Honest limitations (say these in Q&A)

- AQI is an **hourly estimate**; CPCB official values use 24 h / 8 h averages.
- Open-Meteo values are model/analysis-based, not ground-sensor readings; validate against CPCB where possible.
- "Reasons" are statistical contributing factors, **not** proven pollution sources.
- Policy simulator uses **assumed** source shares; outputs are scenario estimates.
- Zone populations are rough planning numbers. Health advice is informational, not medical.

## Structure

```
app.py  pages/  src/  data/  models/  scripts/  tests/  train_model.py  requirements.txt
```
