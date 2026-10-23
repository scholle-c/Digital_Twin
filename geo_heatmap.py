"""
Gemeinsame Geo-Heatmap (pydeck) für Kundenportal und Berater-Dashboard.

    from geo_heatmap import load_incidents_df, load_disasters_df, render_heatmap, heat_points_for_step

Die Karte zeigt Vorfälle als Dichte (gewichtet), Naturereignisse als Kreise und optional den Wohnort.
heat_points_for_step() liefert die Punkte für einen Zeitschritt: Vergangenheit = echte Vorfälle im
rollierenden 12-Monats-Fenster, Zukunft = Vorfallorte gewichtet mit der Prognose aus forecast.py.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pydeck as pdk
import streamlit as st

DATA_DIR = Path(__file__).parent / "generated_demodata"
TODAY = pd.Timestamp("2026-10-23")

# Einfarbige Skala (hell -> dunkel), identisch im Portal und im Dashboard.
HEAT_RANGE = [[205, 226, 251], [158, 197, 244], [109, 167, 236], [57, 135, 229], [37, 106, 191], [16, 66, 129]]

INCIDENT_GROUPS = {
    "burglary": "Einbruch & Diebstahl", "attempted_burglary": "Einbruch & Diebstahl",
    "theft": "Einbruch & Diebstahl", "bicycle_theft": "Einbruch & Diebstahl", "vehicle_theft": "Einbruch & Diebstahl",
    "fire": "Feuer & Elektro", "lightning_surge": "Feuer & Elektro",
    "water_damage": "Leitungswasser",
    "vandalism": "Vandalismus & Glas", "glass_breakage": "Vandalismus & Glas",
    "cyber_fraud": "Cyber & Betrug",
}
INCIDENT_LABELS = {
    "burglary": "Einbruch", "attempted_burglary": "Einbruchsversuch", "theft": "Diebstahl",
    "bicycle_theft": "Fahrraddiebstahl", "vehicle_theft": "Kfz-Diebstahl", "fire": "Brand",
    "lightning_surge": "Überspannung", "water_damage": "Leitungswasser", "vandalism": "Vandalismus",
    "glass_breakage": "Glasbruch", "cyber_fraud": "Online-Betrug",
}
DISASTER_LABELS = {
    "heavy_rain": "Starkregen", "flood": "Hochwasser", "storm": "Sturm", "hail": "Hagel", "heatwave": "Hitze",
    "wildfire": "Waldbrand", "earthquake": "Erdbeben", "landslide": "Erdrutsch", "avalanche": "Lawine",
    "snow_load": "Schneelast", "volcanic_eruption": "Vulkanausbruch",
}
# Kennzahl aus forecast.py -> Vorfallgruppe auf der Karte
METRIC_GROUPS = {"einbrueche": "Einbruch & Diebstahl", "feueralarme": "Feuer & Elektro", "wasserschaeden": "Leitungswasser"}


# ---------- Daten ----------
@st.cache_data(show_spinner=False)
def load_incidents_df() -> pd.DataFrame:
    path = DATA_DIR / "incidents.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path, dtype={"postal_code": str, "customer_id": str})
    df["incident_date"] = pd.to_datetime(df["incident_date"])
    df["group"] = df["incident_type"].map(INCIDENT_GROUPS).fillna("Sonstiges")
    df["label"] = df["incident_type"].map(INCIDENT_LABELS).fillna(df["incident_type"])
    return df


@st.cache_data(show_spinner=False)
def load_disasters_df() -> pd.DataFrame:
    path = DATA_DIR / "disaster.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    df["start_date"] = pd.to_datetime(df["start_date"])
    df["label"] = df["disaster_type"].map(DISASTER_LABELS).fillna(df["disaster_type"])
    return df


# ---------- Zeitschritt ----------
def heat_points_for_step(incidents: pd.DataFrame, metric: str, step: int, region: str | None = None) -> pd.DataFrame:
    """Punkte (longitude, latitude, weight, tip) für Monat `step` relativ zu heute (<= 0 Vergangenheit, > 0 Prognose)."""
    group = METRIC_GROUPS[metric]
    data = incidents[incidents["group"] == group]
    if region:
        data = data[data["region"] == region]
    if step <= 0:
        end = TODAY + pd.DateOffset(months=step)
        window = data[(data["incident_date"] <= end) & (data["incident_date"] > end - pd.DateOffset(months=12))]
        return window.assign(weight=window["severity_level"].astype(float),
                             tip=window["label"] + " · " + window["city"] + " · " + window["incident_date"].dt.strftime("%d.%m.%Y"))
    # Zukunft: alle bekannten Orte, gewichtet mit Prognose / heutigem Niveau je Bundesland
    import forecast as fc
    now, future = fc.heatmap_frame(metric, 0), fc.heatmap_frame(metric, step)
    factor = {r: future[r] / now[r] if now.get(r) else 1.0 for r in future}
    return data.assign(weight=data["severity_level"].astype(float) * data["region"].map(factor).fillna(1.0),
                       tip=data["label"] + " · " + data["city"] + " · Prognose +" + str(step) + " Mon.")


# ---------- Karte ----------
def render_heatmap(points: pd.DataFrame, nature: pd.DataFrame | None = None, home: tuple[float, float] | None = None,
                   center: tuple[float, float] | None = None, zoom: float | None = None, height: int = 380,
                   key: str | None = None) -> None:
    """Zeichnet die Heatmap. points braucht longitude, latitude, weight, tip."""
    layers = []
    if not points.empty:
        layers += [
            pdk.Layer("HeatmapLayer", points, get_position=["longitude", "latitude"], get_weight="weight",
                      radius_pixels=45, color_range=HEAT_RANGE, opacity=0.75),
            pdk.Layer("ScatterplotLayer", points, get_position=["longitude", "latitude"], get_radius=1800,
                      radius_min_pixels=3, get_fill_color=[16, 66, 129, 170], pickable=True),
        ]
    if home:
        layers.append(pdk.Layer("ScatterplotLayer", pd.DataFrame([{"lon": home[1], "lat": home[0], "tip": "Wohnort"}]),
                                get_position=["lon", "lat"], get_radius=2500, radius_min_pixels=7,
                                get_fill_color=[0, 55, 129, 255], get_line_color=[255, 255, 255],
                                line_width_min_pixels=2, stroked=True, pickable=True))
    if nature is not None and not nature.empty:
        nat = nature.assign(tip=nature["label"] + " · " + nature["city"] + " · Stufe " + nature["severity_level"].astype(str))
        nat = nat.assign(color=nat["status"].map(lambda s: [208, 59, 59, 210] if s in ("active", "forecast") else [100, 116, 139, 150]))
        layers.append(pdk.Layer("ScatterplotLayer", nat, get_position=["longitude", "latitude"],
                                get_radius="affected_radius_km * 300", radius_min_pixels=5, get_fill_color="color",
                                stroked=True, get_line_color=[255, 255, 255], line_width_min_pixels=1, pickable=True))
    if center is None:
        center = (points["latitude"].mean(), points["longitude"].mean()) if not points.empty else (51.1, 10.4)
    deck = pdk.Deck(layers=layers,
                    initial_view_state=pdk.ViewState(latitude=center[0], longitude=center[1], zoom=zoom or 4.8),
                    tooltip={"text": "{tip}"}, map_provider="carto",
                    map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json")
    st.pydeck_chart(deck, height=height, key=key)
