import plotly.graph_objects as go
import streamlit as st

from src.aqi_calculator import category, colour
from src.ui import forecast_for, location_df, sidebar

st.set_page_config(page_title="AQI Forecast", page_icon="\U0001F4C8", layout="wide")
df, mode, loc = sidebar()
st.title(f"AQI Forecast \u2014 {loc}")

fc = forecast_for(df, loc)
g = location_df(df, loc)
if fc["warning"]:
    st.warning(fc["warning"])

cols = st.columns(4)
cols[0].metric("Now", f"{fc['current']:.0f}", fc["category"], delta_color="off")
for col, h in zip(cols[1:], (6, 12, 24)):
    r = fc["horizons"][h]
    col.metric(f"In {h} hours", r["aqi"], f"{r['category']}  (range {r['low']}\u2013{r['high']})", delta_color="off")

st.subheader("Probability of Poor or worse (AQI > 200)")
pc = st.columns(3)
for col, h in zip(pc, (6, 12, 24)):
    col.progress(min(1.0, fc["horizons"][h]["p_poor"]), text=f"{h} h: {fc['horizons'][h]['p_poor']*100:.0f}%")

recent = g.tail(36)
hist_t, hist_y = recent["time"], recent["aqi"]
fig = go.Figure()
fig.add_trace(go.Scatter(x=hist_t, y=hist_y, name="Observed", line=dict(width=3)))
ft = [g["time"].iloc[-1]] + [fc["horizons"][h]["time"] for h in (6, 12, 24)]
fy = [fc["current"]] + [fc["horizons"][h]["aqi"] for h in (6, 12, 24)]
fig.add_trace(go.Scatter(x=ft, y=fy, name="Forecast", line=dict(width=3, dash="dash", color="#e03b2f")))
fig.add_trace(go.Scatter(x=ft[1:] + ft[:0:-1], y=[fc["horizons"][h]["high"] for h in (6, 12, 24)] +
                         [fc["horizons"][h]["low"] for h in (24, 12, 6)],
                         fill="toself", fillcolor="rgba(224,59,47,0.15)", line=dict(width=0),
                         name="80% range", hoverinfo="skip"))
fig.add_hline(y=200, line_dash="dot", line_color="#999", annotation_text="Poor threshold")
fig.update_layout(height=420, yaxis_title="AQI", margin=dict(l=10, r=10, t=10, b=10))
st.plotly_chart(fig, use_container_width=True)

st.subheader("Why is AQI expected to change?")
for r in fc["reasons"]:
    st.write(f"\u2022 {r}")
st.caption("These are statistical contributing factors from recent data. They are not proof of the "
           f"actual pollution source. Model used (6 h): {fc['model']}.")
