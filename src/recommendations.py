"""Health advice, authority actions and the (illustrative) policy-scenario simulator."""
from __future__ import annotations
from .aqi_calculator import compute_aqi, category

PROFILES = ["General adult", "Child", "Elderly person", "Asthma patient", "Outdoor worker", "Athlete"]
DISCLAIMER = "General informational guidance only - not medical advice or diagnosis."


def health_advice(profile: str, aqi: float, safe_window: str = "8 AM - 10 AM") -> list:
    cat = category(aqi)
    sensitive = profile in {"Child", "Elderly person", "Asthma patient"}
    tips = []
    if aqi <= 50:
        return ["Air quality is good - normal outdoor activity is fine."]
    if aqi <= 100:
        tips.append("Air is acceptable; unusually sensitive people may notice mild symptoms.")
        if profile == "Asthma patient":
            tips.append("Keep your prescribed medication within reach when outdoors.")
        return tips
    if aqi <= 200:  # Moderate
        tips.append("Limit long or intense outdoor exercise." if sensitive else
                    "Reduce prolonged heavy exertion outdoors.")
        if profile == "Asthma patient":
            tips += ["Keep prescribed medication available", "Watch for breathlessness or wheezing"]
        if profile == "Outdoor worker":
            tips.append("Take regular breaks in cleaner indoor air; consider an N95 mask.")
    else:
        tips.append(f"Air is {cat}: avoid outdoor exercise during the peak period.")
        tips.append("Close windows during the peak period; use an air purifier if available.")
        tips.append(f"Prefer outdoor activity during {safe_window}, when air is usually cleaner.")
        if profile == "Asthma patient":
            tips += ["Keep prescribed medication available", "Follow your doctor's asthma action plan"]
        if profile in {"Child", "Elderly person"}:
            tips.append("Keep outdoor time short; prefer indoor play/rest.")
        if profile in {"Outdoor worker", "Athlete"}:
            tips += ["Move training indoors or postpone it", "Wear a well-fitted N95/FFP2 mask if you must be outside"]
        if aqi > 300:
            tips.append("Everyone should minimise outdoor exposure; seek medical help for severe symptoms.")
    return tips


def safest_window(hourly_pred: dict | None = None) -> str:
    """Placeholder rule: Delhi-NCR air is typically cleanest mid-afternoon and mid-morning."""
    return "8 AM - 10 AM"


AUTHORITY_ACTIONS = {
    "pm10": ["Increase road-water sprinkling in construction-heavy areas",
             "Enforce dust-control covers at construction sites"],
    "pm25": ["Inspect and act on waste-burning reports",
             "Deploy mobile monitoring units to confirm the hotspot"],
    "no2":  ["Temporarily restrict heavy vehicles in the hotspot",
             "Increase public-transport frequency"],
    "co":   ["Manage traffic congestion at key junctions"],
    "so2":  ["Check industrial emission compliance nearby"],
    "o3":   ["Issue midday outdoor-activity advisory"],
}


def authority_actions(aqi_pred: float, dominant: str) -> list:
    acts = list(AUTHORITY_ACTIONS.get(dominant, []))
    if aqi_pred > 200:
        acts.append("Issue school outdoor-activity advisory")
    if aqi_pred > 300:
        acts += ["Consider temporary restrictions on heavy vehicles and construction activity",
                 "Activate public health alert for vulnerable groups"]
    return acts or ["Continue routine monitoring"]
    # NOTE: the system only RECOMMENDS; humans decide and enforce.


# Illustrative source shares of PM (ASSUMPTIONS for the simulator, not measured data).
SOURCE_SHARES = {"traffic": 0.35, "construction_dust": 0.25, "waste_burning": 0.15}


def simulate_scenario(pollutants: dict, traffic_cut=0.0, dust_cut=0.0, burning_cut=0.0) -> dict:
    """Scale PM2.5/PM10 by assumed source shares; returns before/after AQI.
    Label every output 'scenario estimate, not a guaranteed outcome'."""
    f = 1 - (SOURCE_SHARES["traffic"] * traffic_cut + SOURCE_SHARES["construction_dust"] * dust_cut
             + SOURCE_SHARES["waste_burning"] * burning_cut)
    base, _ = compute_aqi(pollutants)
    scen_vals = dict(pollutants)
    for k in ("pm25", "pm10"):
        if scen_vals.get(k) is not None:
            scen_vals[k] = scen_vals[k] * f
    scen, dom = compute_aqi(scen_vals)
    gain = 0 if base == 0 else (base - scen) / base * 100
    return {"baseline": base, "scenario": scen, "improvement_pct": gain, "dominant": dom}
