"""AirWise City - City Overview (home page).  Run:  streamlit run app.py"""
import plotly.graph_objects as go
import streamlit as st

from src.aqi_calculator import POLLUTANT_LABELS, category, colour
from src.ui import aqi_badge, forecast_for, location_df, pol_label, sidebar

st.set_page_config(page_title="AirWise City", page_icon="\U0001F32B\uFE0F", layout="wide")
df, mode, loc = sidebar()

st.title("AirWise City")
st.caption("AI-powered AQI forecasting, citizen warnings and urban action \u2014 pilot: Ghaziabad / Delhi NCR")

g = location_df(df, loc)
now = g.iloc[-1]
fc = forecast_for(df, loc)

c1, c2, c3, c4 = st.columns([1.3, 1, 1, 1])
c1.metric(f"Estimated AQI \u2014 {loc}", f"{now['aqi']:.0f}")
with c1:
    aqi_badge(now["aqi"])
c2.metric("Dominant pollutant", pol_label(now["dominant"]))
c3.metric("6-hour forecast", f"{fc['horizons'][6]['aqi']}", delta=f"{fc['horizons'][6]['aqi'] - now['aqi']:+.0f}",
          delta_color="inverse")
c4.metric("Last data update", now["time"].strftime("%d %b, %H:%M"))

if fc["horizons"][6]["category"] in ("Poor", "Very Poor", "Severe"):
    st.warning(f"Air is predicted to reach **{fc['horizons'][6]['category']}** within 6 hours. "
               f"See the Health Advisor for profile-specific precautions.")
if fc["warning"]:
    st.info(fc["warning"])

st.subheader("Pollutants and weather")
cols = st.columns(6)
units = {"pm25": "\u00b5g/m\u00b3", "pm10": "\u00b5g/m\u00b3", "no2": "\u00b5g/m\u00b3",
         "so2": "\u00b5g/m\u00b3", "co": "mg/m\u00b3", "o3": "\u00b5g/m\u00b3"}
for col, p in zip(cols, ["pm25", "pm10", "no2", "so2", "co", "o3"]):
    v = now.get(p)
    col.metric(POLLUTANT_LABELS[p], "n/a" if v != v else f"{v:.1f}", units[p])
w1, w2, w3 = st.columns(3)
w1.metric("Temperature", f"{now['temp']:.1f} \u00b0C")
w2.metric("Humidity", f"{now['humidity']:.0f} %")
w3.metric("Wind speed", f"{now['wind']:.1f} km/h")

st.subheader("Last 48 hours")
recent = g.tail(48)
fig = go.Figure()
fig.add_trace(go.Scatter(x=recent["time"], y=recent["aqi"], mode="lines+markers", name="AQI",
                         line=dict(color=colour(now["aqi"]), width=3)))
for y, name in [(100, "Satisfactory"), (200, "Moderate"), (300, "Poor"), (400, "Very Poor")]:
    fig.add_hline(y=y, line_dash="dot", line_color="#999", annotation_text=f"{name} \u2191", annotation_position="right")
fig.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="AQI", xaxis_title=None)
st.plotly_chart(fig, use_container_width=True)

with st.expander("About the AQI used here"):
    st.write("AQI follows India's CPCB categories (0\u201350 Good, 51\u2013100 Satisfactory, 101\u2013200 Moderate, "
             "201\u2013300 Poor, 301\u2013400 Very Poor, 401\u2013500 Severe). Values are an **hourly estimate** computed "
             "from hourly concentrations, so they can differ from official 24-hour CPCB bulletins.")
