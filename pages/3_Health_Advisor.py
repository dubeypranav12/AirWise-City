import streamlit as st

from src.aqi_calculator import category
from src.recommendations import DISCLAIMER, PROFILES, health_advice, safest_window
from src.ui import aqi_badge, forecast_for, sidebar

st.set_page_config(page_title="Health Advisor", page_icon="\U0001FA7A", layout="wide")
df, mode, loc = sidebar()
st.title(f"Citizen Health Advisor \u2014 {loc}")

profile = st.selectbox("Who is this advice for?", PROFILES, index=3)
fc = forecast_for(df, loc)
when = st.radio("Plan for", ["Now", "In 6 hours", "In 12 hours", "In 24 hours"], horizontal=True, index=1)
aqi = fc["current"] if when == "Now" else fc["horizons"][int(when.split()[1])]["aqi"]

st.metric(f"AQI ({when.lower()})", f"{aqi:.0f}")
aqi_badge(aqi)
st.subheader(f"Advice for: {profile}")
for tip in health_advice(profile, aqi, safest_window()):
    st.write(f"\u2022 {tip}")
st.caption(DISCLAIMER)
