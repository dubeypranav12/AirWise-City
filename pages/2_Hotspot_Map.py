import pandas as pd
import pydeck as pdk
import streamlit as st

from src.aqi_calculator import category, rgb
from src.data_loader import LOCATIONS
from src.ui import forecast_for, location_df, pol_label, sidebar

st.set_page_config(page_title="Hotspot Map", page_icon="\U0001F5FA\uFE0F", layout="wide")
df, mode, loc = sidebar()
st.title("Pollution Hotspot Map \u2014 Ghaziabad / Delhi NCR")

horizon = st.radio("Show", ["Current AQI", "6-hour forecast"], horizontal=True)
rows = []
for name, meta in LOCATIONS.items():
    g = location_df(df, name)
    if g.empty:
        continue
    now, fc = g.iloc[-1], forecast_for(df, name)
    val = now["aqi"] if horizon == "Current AQI" else fc["horizons"][6]["aqi"]
    trend = fc["horizons"][6]["aqi"] - now["aqi"]
    rows.append({"name": name, "lat": meta["lat"], "lon": meta["lon"], "value": val,
                 "category": category(val), "current": now["aqi"], "pred6": fc["horizons"][6]["aqi"],
                 "dominant": pol_label(now["dominant"]),
                 "trend": "Rising" if trend > 15 else "Falling" if trend < -15 else "Steady",
                 "colour": rgb(val)})
m = pd.DataFrame(rows)
layer = pdk.Layer("ScatterplotLayer", m, get_position="[lon, lat]", get_fill_color="colour",
                  get_radius=1100, pickable=True, opacity=0.85, stroked=True, get_line_color=[255, 255, 255])
tip = {"html": "<b>{name}</b><br/>Current AQI: {current}<br/>6-h forecast: {pred6} ({category})"
               "<br/>Dominant: {dominant}<br/>Trend: {trend}"}
st.pydeck_chart(pdk.Deck(layers=[layer], tooltip=tip, map_style=None,
                         initial_view_state=pdk.ViewState(latitude=28.68, longitude=77.40, zoom=10.2)))

pick = st.selectbox("Select a zone for details", m["name"])
r = m[m["name"] == pick].iloc[0]
a, b, c, d = st.columns(4)
a.metric("Current AQI", f"{r['current']:.0f}"); b.metric("Predicted (6 h)", f"{r['pred6']}")
c.metric("Dominant pollutant", r["dominant"]); d.metric("Trend", r["trend"])
from src.recommendations import authority_actions
dom_code = location_df(df, pick).iloc[-1]["dominant"]
st.info("**Recommended action:** " + "; ".join(authority_actions(r["pred6"], dom_code)[:2]))
st.dataframe(m[["name", "current", "pred6", "category", "dominant", "trend"]]
             .sort_values("pred6", ascending=False), hide_index=True, use_container_width=True)
st.caption("Legend: green Good \u00b7 yellow Satisfactory \u00b7 orange Moderate \u00b7 red Poor \u00b7 purple Very Poor \u00b7 dark red Severe")
