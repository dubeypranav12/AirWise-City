"""Alerts: Telegram Bot API with in-app fallback. Tokens come from env vars / Streamlit secrets."""
from __future__ import annotations
import os
from datetime import datetime
from pathlib import Path
import pandas as pd
import requests

HISTORY = Path(__file__).resolve().parent.parent / "data" / "alert_history.csv"


def build_message(location: str, current: float, pred: float, hours: int, cat: str, reason: str) -> str:
    return (f"AirWise City alert - {location}\n"
            f"Current AQI {current:.0f}. Predicted AQI in {hours}h: {pred:.0f} ({cat}).\n"
            f"Main reason: {reason}\n"
            f"General guidance only - check the app for personalised advice.")


def send_telegram(text: str, token: str | None = None, chat_id: str | None = None):
    """Return (ok, info). Never raises - the demo must survive Telegram being unavailable."""
    token = token or os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False, "Telegram not configured (set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)."
    try:
        r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                          json={"chat_id": chat_id, "text": text}, timeout=8)
        return (r.ok, "Sent via Telegram." if r.ok else f"Telegram error {r.status_code}")
    except Exception as exc:
        return False, f"Telegram unavailable ({type(exc).__name__}). Shown in-app instead."


def log_alert(location: str, aqi_pred: float, channel: str, text: str) -> None:
    row = pd.DataFrame([{"sent_at": datetime.now().isoformat(timespec="seconds"),
                         "location": location, "predicted_aqi": round(aqi_pred),
                         "channel": channel, "message": text}])
    row.to_csv(HISTORY, mode="a", header=not HISTORY.exists(), index=False)


def read_history() -> pd.DataFrame:
    return pd.read_csv(HISTORY) if HISTORY.exists() else pd.DataFrame(
        columns=["sent_at", "location", "predicted_aqi", "channel", "message"])
