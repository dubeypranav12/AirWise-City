import numpy as np
import pandas as pd
from src.aqi_calculator import add_aqi_columns, category, compute_aqi, sub_index
from src.alert_service import send_telegram
from src.data_cleaner import clean
from src.data_loader import load_demo
from src.predictor import forecast_location
from src.recommendations import health_advice, simulate_scenario


def test_category_boundaries():
    assert category(50) == "Good" and category(51) == "Satisfactory"
    assert category(200) == "Moderate" and category(201) == "Poor"
    assert category(401) == "Severe"


def test_sub_index_breakpoints():
    assert sub_index("pm25", 30) == 50 and sub_index("pm25", 60) == 100
    assert sub_index("pm25", 1000) == 500
    assert np.isnan(sub_index("pm25", np.nan))


def test_dominant_pollutant():
    aqi, dom = compute_aqi({"pm25": 100, "pm10": 120, "no2": 30})
    assert dom == "pm25" and 200 < aqi <= 300


def test_missing_pollutants_do_not_crash():
    aqi, dom = compute_aqi({"pm25": 80, "pm10": None})
    assert dom == "pm25" and not np.isnan(aqi)
    assert np.isnan(compute_aqi({})[0])


def _demo(kind="moderate_to_poor"):
    return add_aqi_columns(clean(load_demo(kind)))


def test_forecast_with_and_without_model():
    g = _demo()
    g = g[g.location == "Indirapuram"]
    f = forecast_location(g)
    assert set(f["horizons"]) == {6, 12, 24}
    f_fallback = forecast_location(g, None)         # model file unavailable
    assert f_fallback["warning"] and f_fallback["horizons"][6]["aqi"] == round(f_fallback["current"])


def test_demo_scenarios_levels():
    normal = _demo("normal").groupby("location")["aqi"].last().mean()
    severe = _demo("severe").groupby("location")["aqi"].last().mean()
    assert normal < 150 < 300 < severe


def test_health_advice_asthma_poor():
    tips = " ".join(health_advice("Asthma patient", 230)).lower()
    assert "medication" in tips and "avoid outdoor exercise" in tips


def test_simulator_reduces_aqi():
    r = simulate_scenario({"pm25": 150, "pm10": 220}, 0.3, 0.5, 0.5)
    assert r["scenario"] < r["baseline"] and r["improvement_pct"] > 0


def test_telegram_failure_is_graceful(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    ok, info = send_telegram("hi")
    assert ok is False and "not configured" in info
