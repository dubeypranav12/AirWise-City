import pandas as pd
import streamlit as st

from src.alert_service import build_message, log_alert, read_history, send_telegram
from src.data_loader import LOCATIONS
from src.recommendations import SOURCE_SHARES, authority_actions, simulate_scenario
from src.ui import forecast_for, location_df, pol_label, sidebar

st.set_page_config(page_title="Authority Console", page_icon="\U0001F3DB\uFE0F", layout="wide")
df, mode, loc = sidebar()
st.title("Authority Console")
st.caption("Decision support only: the system recommends actions; it never enforces them.")

# ---------- risk table ----------
rows = []
for name, meta in LOCATIONS.items():
    g = location_df(df, name)
    if g.empty:
        continue
    now, fc = g.iloc[-1], forecast_for(df, name)
    p6 = fc["horizons"][6]
    peak_h = max(fc["horizons"], key=lambda h: fc["horizons"][h]["aqi"])
    rows.append({"Zone": name, "Current AQI": int(now["aqi"]), "Predicted 6h": p6["aqi"],
                 "Category (6h)": p6["category"], "Dominant": pol_label(now["dominant"]),
                 "Change (6h)": int(p6["aqi"] - now["aqi"]),
                 "Expected peak": fc["horizons"][peak_h]["time"].strftime("%d %b %H:%M"),
                 "P(Poor+) 6h": round(p6["p_poor"] * 100),
                 "Citizens potentially affected": meta["pop"] if p6["aqi"] > 200 else 0,
                 "_dom": now["dominant"]})
risk = pd.DataFrame(rows).sort_values("Predicted 6h", ascending=False)
st.subheader("Highest-risk zones")
st.dataframe(risk.drop(columns="_dom"), hide_index=True, use_container_width=True)
st.caption("Population figures are rough planning assumptions, not census data.")

worsening = risk[risk["Change (6h)"] > 30]
if not worsening.empty:
    st.warning("Rapidly worsening: " + ", ".join(worsening["Zone"]))

# ---------- recommended interventions ----------
st.subheader("Recommended interventions")
for _, r in risk.head(3).iterrows():
    with st.expander(f"{r['Zone']} \u2014 predicted {r['Predicted 6h']} ({r['Category (6h)']})", expanded=True):
        for a in authority_actions(r["Predicted 6h"], r["_dom"]):
            st.write(f"\u2022 {a}")

# ---------- alerts ----------
st.subheader("Smart alerts")
a1, a2 = st.columns(2)
thr = a1.slider("Alert when 6-hour predicted AQI crosses", 100, 400, 200, step=50)
target = a2.selectbox("Zone", risk["Zone"])
row = risk[risk["Zone"] == target].iloc[0]
fc = forecast_for(df, target)
msg = build_message(target, row["Current AQI"], row["Predicted 6h"], 6, row["Category (6h)"],
                    fc["reasons"][0])
st.code(msg)
if row["Predicted 6h"] >= thr:
    st.error(f"Threshold crossed: predicted {row['Predicted 6h']} \u2265 {thr}")
else:
    st.success("Threshold not crossed for this zone.")
if st.button("Send alert (Telegram, with in-app fallback)"):
    ok, info = send_telegram(msg)
    log_alert(target, row["Predicted 6h"], "telegram" if ok else "in-app", msg)
    (st.success if ok else st.info)(info)
st.dataframe(read_history().tail(10), hide_index=True, use_container_width=True)

# ---------- report ----------
st.subheader("Daily report")
st.download_button("Download risk report (CSV)", risk.drop(columns="_dom").to_csv(index=False),
                   file_name="airwise_daily_report.csv", mime="text/csv")

# ---------- policy simulator ----------
st.subheader("Policy scenario simulator (stretch feature)")
z = st.selectbox("Zone to simulate", risk["Zone"], key="simzone")
s1, s2, s3 = st.columns(3)
t = s1.slider("Reduce traffic emissions", 0, 30, 0, format="%d%%") / 100
d = s2.slider("Improve construction dust control", 0, 50, 0, format="%d%%") / 100
w = s3.slider("Reduce waste-burning events", 0, 50, 0, format="%d%%") / 100
last = location_df(df, z).iloc[-1]
res = simulate_scenario({k: last.get(k) for k in ["pm25", "pm10", "no2", "so2", "co", "o3"]}, t, d, w)
m1, m2, m3 = st.columns(3)
m1.metric("Baseline AQI (now)", f"{res['baseline']:.0f}")
m2.metric("Scenario AQI", f"{res['scenario']:.0f}")
m3.metric("Estimated improvement", f"{res['improvement_pct']:.0f}%")
st.caption("Scenario estimate, not a guaranteed real-world outcome. Assumed PM source shares: "
           + ", ".join(f"{k.replace('_', ' ')} {v:.0%}" for k, v in SOURCE_SHARES.items())
           + ". Replace with measured source-apportionment data if available.")
