"""
Gemeinsame Geo-Heatmap (pydeck) für Kundenportal und Berater-Dashboard.

    from geo_heatmap import load_incidents_df, load_disasters_df, render_heatmap, heat_points_for_step

Die Karte zeigt Vorfälle als Dichte (gewichtet), Naturereignisse als Kreise und optional den Wohnort.
heat_points_for_step() liefert die Punkte für einen Zeitschritt: Vergangenheit = echte Vorfälle im
rollierenden 12-Monats-Fenster, Zukunft = Vorfallorte gewichtet mit der Prognose aus forecast.py.
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

import numpy as np
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
# Welche Naturereignisse zu welcher Kennzahl passen (Einbruch: keine)
METRIC_DISASTERS = {"wasserschaeden": ["heavy_rain", "flood", "storm", "hail", "snow_load"],
                    "feueralarme": ["wildfire", "heatwave"], "einbrueche": []}
# Kontrastreiche Skala für die Dashboard-Karte (hellblau -> gelb -> orange -> rot)
HEAT_RANGE_CONTRAST = [[198, 219, 239], [107, 174, 214], [255, 237, 160], [254, 178, 76], [240, 59, 32], [153, 0, 13]]


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


# ---------- Demo-Punktwolken ----------
# Städte-Cluster je Bundesland: (lat, lon, Gewicht ~ Größe). Synthetisch, nur für die Kartendichte.
CITY_CLUSTERS = {
    "Bayern": [("München", 48.14, 11.58, 1.0), ("Nürnberg", 49.45, 11.08, 0.6), ("Augsburg", 48.37, 10.90, 0.4),
               ("Würzburg", 49.79, 9.95, 0.3), ("Regensburg", 49.01, 12.10, 0.3), ("Bayreuth", 49.95, 11.58, 0.25)],
    "Baden-Württemberg": [("Stuttgart", 48.78, 9.18, 0.9), ("Karlsruhe", 49.01, 8.40, 0.4), ("Freiburg", 47.99, 7.85, 0.35),
                          ("Mannheim", 49.49, 8.47, 0.4), ("Ulm", 48.40, 9.99, 0.25)],
    "Berlin": [("Berlin", 52.52, 13.40, 1.2)],
    "Brandenburg": [("Potsdam", 52.40, 13.06, 0.3), ("Cottbus", 51.76, 14.33, 0.2)],
    "Bremen": [("Bremen", 53.08, 8.80, 0.45)],
    "Hamburg": [("Hamburg", 53.55, 10.00, 1.0)],
    "Hessen": [("Frankfurt", 50.11, 8.68, 0.9), ("Kassel", 51.31, 9.49, 0.3), ("Darmstadt", 49.87, 8.65, 0.3)],
    "Mecklenburg-Vorpommern": [("Rostock", 54.09, 12.14, 0.3), ("Schwerin", 53.63, 11.41, 0.2)],
    "Niedersachsen": [("Hannover", 52.37, 9.73, 0.7), ("Braunschweig", 52.27, 10.52, 0.35), ("Oldenburg", 53.14, 8.21, 0.3),
                      ("Osnabrück", 52.28, 8.05, 0.3), ("Göttingen", 51.53, 9.93, 0.25)],
    "Nordrhein-Westfalen": [("Köln", 50.94, 6.96, 1.0), ("Düsseldorf", 51.23, 6.78, 0.7), ("Dortmund", 51.51, 7.47, 0.6),
                            ("Essen", 51.46, 7.01, 0.6), ("Münster", 51.96, 7.63, 0.4), ("Bielefeld", 52.02, 8.53, 0.35),
                            ("Aachen", 50.78, 6.08, 0.3), ("Bonn", 50.74, 7.10, 0.35)],
    "Rheinland-Pfalz": [("Mainz", 50.00, 8.27, 0.4), ("Koblenz", 50.36, 7.59, 0.3), ("Trier", 49.75, 6.64, 0.25),
                        ("Bad Neuenahr-Ahrweiler", 50.54, 7.11, 0.2)],
    "Saarland": [("Saarbrücken", 49.24, 6.99, 0.35)],
    "Sachsen": [("Leipzig", 51.34, 12.37, 0.7), ("Dresden", 51.05, 13.74, 0.7), ("Chemnitz", 50.83, 12.92, 0.35)],
    "Sachsen-Anhalt": [("Magdeburg", 52.13, 11.63, 0.35), ("Halle", 51.48, 11.97, 0.3)],
    "Schleswig-Holstein": [("Kiel", 54.32, 10.14, 0.4), ("Lübeck", 53.87, 10.69, 0.3), ("Flensburg", 54.78, 9.44, 0.2)],
    "Thüringen": [("Erfurt", 50.98, 11.03, 0.35), ("Jena", 50.93, 11.59, 0.25)],
}
POINTS_PER_CITY = 60


def _level(metric: str, region: str, step: int) -> float:
    """Niveau der Kennzahl in der Region für den Zeitschritt (Historie bzw. Prognose), relativ zu heute."""
    import forecast as fc
    if region not in fc.regions():
        return 1.0
    now = fc.heatmap_frame(metric, 0)[region]
    then = fc.heatmap_frame(metric, step)[region] if step != 0 else now
    ratio = (then / now) if now else 1.0
    return min(max(ratio, 0.4), 2.2)       # begrenzt, damit die Karte deutlich, aber nicht absurd reagiert


@st.cache_data(show_spinner=False)
def demo_points(metric: str, step: int, region: str | None = None) -> pd.DataFrame:
    """Synthetische Punktwolke um Städte, gewichtet mit dem regionalen Niveau des Zeitschritts.

    Demo-Daten zur Veranschaulichung der Dichte, keine echten Vorfälle. Die Form der Wolke ist fix (Seed),
    nur die Gewichte ändern sich mit der Zeit, damit die Entwicklung je Region sichtbar wird.
    """
    rng = np.random.default_rng(42)
    rows = []
    for state, cities in CITY_CLUSTERS.items():
        if region and state != region:
            continue
        level = _level(metric, state, step)
        for city, lat, lon, size in cities:
            n = int(POINTS_PER_CITY * size)
            lats = lat + rng.normal(0, 0.12, n)
            lons = lon + rng.normal(0, 0.18, n)
            w = rng.gamma(2.0, 0.5, n) * level ** 2          # Quadrat verstärkt den Unterschied zwischen den Zeitschritten
            rows += [{"longitude": float(x), "latitude": float(y), "weight": float(v), "region": state,
                      "tip": f"{city} · Demo-Dichte"} for x, y, v in zip(lons, lats, w)]
    return pd.DataFrame(rows)


# ---------- Zeitschritt ----------
def heat_points_for_step(incidents: pd.DataFrame, metric: str, step: int, region: str | None = None,
                         demo: bool = True) -> pd.DataFrame:
    """Punkte (longitude, latitude, weight, tip) für Monat `step` relativ zu heute (<= 0 Vergangenheit, > 0 Prognose).

    Mit demo=True kommen zusätzlich synthetische Punktwolken dazu, damit die Karte Fläche hat.
    """
    real = _real_points_for_step(incidents, metric, step, region)
    if not demo:
        return real
    return pd.concat([demo_points(metric, step, region), real.assign(weight=real["weight"] * 3)], ignore_index=True)


def _real_points_for_step(incidents: pd.DataFrame, metric: str, step: int, region: str | None = None) -> pd.DataFrame:
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
    return data.assign(weight=data["severity_level"].astype(float) * data["region"].map(factor).astype(float).fillna(1.0),
                       tip=data["label"] + " · " + data["city"] + " · Prognose +" + str(step) + " Mon.")


# ---------- Karte ----------
def render_heatmap(points: pd.DataFrame, nature: pd.DataFrame | None = None, home: tuple[float, float] | None = None,
                   center: tuple[float, float] | None = None, zoom: float | None = None, height: int | Literal["stretch"] = 380,
                   key: str | None = None, color_domain: list[float] | None = None, markers: bool = True,
                   color_range: list[list[int]] | None = None, radius_pixels: int = 45) -> None:
    """Zeichnet die Heatmap. points braucht longitude, latitude, weight, tip.

    color_domain fixiert die Farbskala (z. B. [0, 40]); ohne Angabe normalisiert pydeck pro Ansicht,
    dann sehen alle Zeitschritte gleich aus. markers=False blendet die Einzelpunkte aus (Demo-Wolken).
    """
    layers = []
    if not points.empty:
        heat_kwargs = {"color_domain": color_domain} if color_domain else {}
        layers.append(pdk.Layer("HeatmapLayer", points, get_position=["longitude", "latitude"], get_weight="weight",
                                radius_pixels=radius_pixels, color_range=color_range or HEAT_RANGE, opacity=0.8,
                                aggregation="SUM", **heat_kwargs))
        marker_points = points[~points["tip"].str.contains("Demo-Dichte", na=False)] if markers else points.iloc[0:0]
        if not marker_points.empty:
            layers.append(pdk.Layer("ScatterplotLayer", marker_points, get_position=["longitude", "latitude"],
                                    get_radius=1800, radius_min_pixels=3, get_fill_color=[16, 66, 129, 170], pickable=True))
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
