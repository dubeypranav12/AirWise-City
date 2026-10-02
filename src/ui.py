"""Shared Streamlit helpers: sidebar, cached data access, small formatting utilities."""
import pandas as pd
import streamlit as st

from .aqi_calculator import POLLUTANT_LABELS, category, colour
from .data_cleaner import clean
from .data_loader import DEFAULT_LOCATION, LOCATIONS, get_data
from .predictor import forecast_location, load_bundle


@st.cache_data(ttl=600, show_spinner="Loading air-quality data...")
def _data(mode: str, scenario: str):
    df, used, msg = get_data(mode, scenario)
    return clean(df).pipe(_reaqi), used, msg


def _reaqi(df):
    from .aqi_calculator import add_aqi_columns
    return add_aqi_columns(df)


@st.cache_resource
def _bundle():
    return load_bundle()


def sidebar():
    """Render the shared sidebar; returns (df, mode_used, location)."""
    st.sidebar.title("AirWise City")
    mode = st.sidebar.radio("Data mode", ["Live", "Cached", "Demo"], key="mode",
                            help="Live = Open-Meteo API; Cached = last download; Demo = replay a prepared event")
    scenario = "moderate_to_poor"
    if mode == "Demo":
        scenario = st.sidebar.selectbox("Demo scenario", ["normal", "moderate_to_poor", "severe"], index=1,
                                        key="scenario")
    df, used, msg = _data(mode, scenario)
    st.sidebar.caption(f"Active mode: **{used}**  \n{msg}")
    if st.sidebar.button("Refresh data"):
        st.cache_data.clear(); st.rerun()
    loc = st.sidebar.selectbox("Location", list(LOCATIONS), index=list(LOCATIONS).index(DEFAULT_LOCATION),
                               key="location")
    return df, used, loc


def location_df(df, loc):
    return df[df["location"] == loc].sort_values("time")


def forecast_for(df, loc):
    return forecast_location(location_df(df, loc), _bundle())


def aqi_badge(aqi):
    st.markdown(f"<span style='background:{colour(aqi)};color:white;padding:2px 10px;border-radius:10px;"
                f"font-weight:600'>{category(aqi)}</span>", unsafe_allow_html=True)


def pol_label(code):
    return POLLUTANT_LABELS.get(code, str(code))
