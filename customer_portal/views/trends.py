"""
Trends & Analysen: regionale Heatmap, Entwicklung nach Risikokategorie, demografische
Trends und persönliche Risikoeinschätzung des Digital Twin.

Alle Werte stammen aus den synthetischen Dateien in generated_demodata/ und sind
ausdrücklich keine offiziellen oder geprüften Daten. Echte Datenquellen lassen sich
später über core/data.py anbinden, ohne diese Seite zu ändern.
"""
from __future__ import annotations

import altair as alt
import pandas as pd
import pydeck as pdk
import streamlit as st

from core.data import HOME_COORDS, TODAY, load_age_group_claims, load_disasters, load_incidents
from ui.components import empty_state, esc, euro, icon, page_header, render_html

# Feste Farbe je Risikokategorie (Farbe folgt der Kategorie, nicht dem Rang). Geprüfte Reihenfolge.
GROUP_COLORS = {
    "Einbruch & Diebstahl": "#2a78d6",
    "Feuer & Elektro": "#eb6834",
    "Leitungswasser": "#1baf7a",
    "Vandalismus & Glas": "#eda100",
    "Cyber & Betrug": "#e87ba4",
}
# Einfarbige Skala (hell -> dunkel) für die Heatmap.
HEAT_RANGE = [[205, 226, 251], [158, 197, 244], [109, 167, 236], [57, 135, 229], [37, 106, 191], [16, 66, 129]]
PERIODS = {"Letzte 3 Monate": 3, "Letzte 6 Monate": 6, "Letzte 12 Monate": 12, "Letzte 24 Monate": 24}
AXIS = {"labelColor": "#475569", "titleColor": "#475569", "gridColor": "#E2E8F0", "domainColor": "#CBD5E1",
        "labelFont": "Inter", "titleFont": "Inter"}


# Baut die Analyseseite auf.
def render(ctx: dict) -> None:
    """Rendert Filter, Kennzahlen, Heatmap und Trenddiagramme."""
    page_header("Trends & Analysen", "Risiken in Ihrer Region und für Ihren Haushalt – verständlich aufbereitet.", "insights")
    render_html(
        f'<div class="dt-callout dt-callout-warn">{icon("science", "ms-sm")}<span><b>Beispieldaten:</b> Alle Werte stammen '
        f"aus synthetischen Testdaten des Projekts. Es handelt sich nicht um offizielle oder geprüfte Allianz-Daten.</span></div>"
    )
    with st.spinner("Analysedaten werden geladen …"):
        incidents, disasters = load_incidents(), load_disasters()
    if incidents.empty:
        empty_state("Keine Analysedaten gefunden", "Die Datei generated_demodata/incidents.csv fehlt.", "database")
        return

    # Filterzeile über allen Diagrammen.
    regions = ["Deutschland gesamt"] + sorted(incidents["region"].unique())
    home_region = "Bayern" if "Bayern" in regions else regions[0]
    f1, f2, f3 = st.columns([1, 1, 2])
    region = f1.selectbox("Region", regions, index=regions.index(home_region), key="trf_region")
    period = f2.selectbox("Zeitraum", list(PERIODS), index=2, key="trf_period")
    groups = f3.multiselect("Risikokategorien", list(GROUP_COLORS), default=list(GROUP_COLORS), key="trf_groups",
                            placeholder="Kategorien wählen")

    months = PERIODS[period]
    start = pd.Timestamp(TODAY) - pd.DateOffset(months=months)
    data = incidents[(incidents["incident_date"] >= start) & incidents["group"].isin(groups)]
    if region != "Deutschland gesamt":
        data = data[data["region"] == region]
    nature = disasters[disasters["country"] == "DE"] if not disasters.empty else disasters
    if region != "Deutschland gesamt" and not nature.empty:
        nature = nature[nature["region"] == region]

    _kpis(data, nature, start)
    if data.empty:
        empty_state("Keine Vorfälle für diese Auswahl", "Erweitern Sie Zeitraum, Region oder Kategorien.", "filter_alt_off")
    else:
        map_col, chart_col = st.columns([1.15, 1], gap="medium")
        with map_col, st.container(key="tr_map"):
            _heatmap(data, nature, region)
        with chart_col, st.container(key="tr_trend"):
            _trend_chart(data, groups, months)

    demo_col, twin_col = st.columns(2, gap="medium")
    with demo_col, st.container(key="tr_demo"):
        _demographics()
    with twin_col, st.container(key="tr_twin"):
        _personal_risk(ctx)


# Vier Kennzahlen mit Tooltips zur Erklärung.
def _kpis(data: pd.DataFrame, nature: pd.DataFrame, start: pd.Timestamp) -> None:
    """Zeigt Kennzahlen zur aktuellen Filterauswahl."""
    near = 0
    if not data.empty:
        near = int((data["postal_code"].str[:2] == st.session_state.profile["postal_code"][:2]).sum())
    upcoming = int(nature["status"].isin(["active", "forecast"]).sum()) if not nature.empty else 0
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Vorfälle", len(data), help="Anzahl der Schadenereignisse im gewählten Zeitraum, Gebiet und in den gewählten Kategorien.")
    c2.metric("Ø Schadenhöhe", euro(data["damage_eur"].mean(), 0) if not data.empty else "–",
              help="Durchschnittlicher Schaden je Vorfall. Einzelne Großschäden (z. B. Brände) heben den Wert stark an.")
    c3.metric("In Ihrer PLZ-Region", near, help="Vorfälle mit denselben ersten zwei Ziffern Ihrer Postleitzahl.")
    c4.metric("Naturereignisse aktiv/erwartet", upcoming,
              help="Aktuelle oder vorhergesagte Ereignisse wie Starkregen oder Hochwasser in der gewählten Region.")


# Regionale Heatmap: Dichte der Vorfälle, Naturereignisse und Ihr Wohnort.
def _heatmap(data: pd.DataFrame, nature: pd.DataFrame, region: str) -> None:
    """Zeigt eine interaktive Karte mit Heatmap und Markern."""
    render_html('<h3 class="dt-h3">Regionale Risiko-Heatmap</h3>')
    points = data.assign(weight=data["severity_level"])[["longitude", "latitude", "weight", "label", "city", "damage_eur"]]
    layers = [
        pdk.Layer("HeatmapLayer", points, get_position=["longitude", "latitude"], get_weight="weight",
                  radius_pixels=45, color_range=HEAT_RANGE, opacity=0.75),
        pdk.Layer("ScatterplotLayer", points.assign(tip=points["label"] + " · " + points["city"]),
                  get_position=["longitude", "latitude"], get_radius=1800, radius_min_pixels=3,
                  get_fill_color=[16, 66, 129, 170], pickable=True),
        pdk.Layer("ScatterplotLayer", pd.DataFrame([{"lon": HOME_COORDS[1], "lat": HOME_COORDS[0], "tip": "Ihr Wohnort"}]),
                  get_position=["lon", "lat"], get_radius=2500, radius_min_pixels=7, get_fill_color=[0, 55, 129, 255],
                  get_line_color=[255, 255, 255], line_width_min_pixels=2, stroked=True, pickable=True),
    ]
    if not nature.empty:
        nat = nature.assign(tip=nature["label"] + " · " + nature["city"] + " · Stufe " + nature["severity_level"].astype(str))
        nat = nat.assign(color=nat["status"].map(lambda s: [208, 59, 59, 210] if s in ("active", "forecast") else [100, 116, 139, 150]))
        layers.append(pdk.Layer("ScatterplotLayer", nat, get_position=["longitude", "latitude"],
                                get_radius="affected_radius_km * 300", radius_min_pixels=5, get_fill_color="color",
                                stroked=True, get_line_color=[255, 255, 255], line_width_min_pixels=1, pickable=True))
    center = (data["latitude"].mean(), data["longitude"].mean()) if region != "Deutschland gesamt" else (51.1, 10.4)
    deck = pdk.Deck(
        layers=layers,
        initial_view_state=pdk.ViewState(latitude=center[0], longitude=center[1], zoom=6 if region != "Deutschland gesamt" else 4.8),
        tooltip={"text": "{tip}"},
        map_provider="carto",
        map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
    )
    st.pydeck_chart(deck, height=380)
    render_html(
        '<div class="dt-legend"><span><i class="dt-sw dt-sw-heat"></i>Dichte der Vorfälle (gewichtet nach Schwere)</span>'
        '<span><i class="dt-sw dt-sw-home"></i>Ihr Wohnort</span>'
        '<span><i class="dt-sw dt-sw-alert"></i>Naturereignis aktiv/erwartet</span>'
        '<span><i class="dt-sw dt-sw-past"></i>Naturereignis vergangen</span></div>'
    )


# Gestapelte Balken: Vorfälle je Monat bzw. Quartal und Kategorie.
def _trend_chart(data: pd.DataFrame, groups: list[str], months: int) -> None:
    """Zeigt die zeitliche Entwicklung der Vorfälle je Risikokategorie."""
    freq_label = "Monat" if months <= 6 else "Quartal"
    render_html(f'<h3 class="dt-h3">Entwicklung nach Kategorie</h3><p class="dt-tiny">Vorfälle pro {freq_label}</p>')
    period = data["incident_date"].dt.to_period("M" if months <= 6 else "Q")
    counts = data.assign(period=period.astype(str)).groupby(["period", "group"]).size().reset_index(name="Vorfälle")
    counts = counts.rename(columns={"period": freq_label, "group": "Kategorie"})
    domain = [g for g in GROUP_COLORS if g in groups]
    chart = (
        alt.Chart(counts)
        .mark_bar(stroke="#ffffff", strokeWidth=2)
        .encode(
            x=alt.X(f"{freq_label}:O", title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("Vorfälle:Q", title="Vorfälle", axis=alt.Axis(tickMinStep=1)),
            color=alt.Color("Kategorie:N", scale=alt.Scale(domain=domain, range=[GROUP_COLORS[g] for g in domain]),
                            legend=alt.Legend(orient="bottom", columns=2, title=None, labelFont="Inter")),
            order=alt.Order("Kategorie:N"),
            tooltip=[f"{freq_label}:O", "Kategorie:N", "Vorfälle:Q"],
        )
        .properties(height=300)
        .configure_axis(**AXIS)
        .configure_view(strokeWidth=0)
        .configure(background="#FFFFFF")
    )
    st.altair_chart(chart, use_container_width=True)
    with st.expander("Daten als Tabelle", icon=":material/table:"):
        st.dataframe(counts, hide_index=True)


# Demografische Trends: Fälle je Altersgruppe (Sach- und Gesundheitsfälle).
def _demographics() -> None:
    """Zeigt Sach- und Gesundheitsfälle je Altersgruppe der Kundinnen und Kunden."""
    render_html('<h3 class="dt-h3">Demografische Trends</h3><p class="dt-tiny">Gemeldete Fälle je Altersgruppe (alle Demokunden)</p>')
    claims = load_age_group_claims()
    if claims.empty:
        empty_state("Keine demografischen Daten", "Kunden- oder Falldaten fehlen.", "groups")
        return
    claims = claims.rename(columns={"age_group": "Altersgruppe", "kind": "Art", "count": "Fälle"})
    chart = (
        alt.Chart(claims)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("Altersgruppe:O", title=None, axis=alt.Axis(labelAngle=0)),
            xOffset="Art:N",
            y=alt.Y("Fälle:Q", axis=alt.Axis(tickMinStep=1)),
            color=alt.Color("Art:N", scale=alt.Scale(domain=["Sachschäden", "Gesundheitsfälle"], range=["#2a78d6", "#eb6834"]),
                            legend=alt.Legend(orient="bottom", title=None, labelFont="Inter")),
            tooltip=["Altersgruppe:O", "Art:N", "Fälle:Q"],
        )
        .properties(height=260)
        .configure_axis(**AXIS)
        .configure_view(strokeWidth=0)
        .configure(background="#FFFFFF")
    )
    st.altair_chart(chart, use_container_width=True)


# Persönliche Risiken laut Digital Twin, mit Treibern als Erklärung.
def _personal_risk(ctx: dict) -> None:
    """Zeigt die Risikoeinschätzung und Lebensereignis-Prognosen des Digital Twin."""
    render_html('<h3 class="dt-h3">Ihr persönliches Risikoprofil</h3>'
                '<p class="dt-tiny">Modellschätzung des Digital Twin für die nächsten 12 Monate – keine bestätigte Tatsache.</p>')
    twin = ctx["twin"]
    if not twin:
        empty_state("Digital Twin nicht verfügbar", "Die persönliche Einschätzung kann gerade nicht berechnet werden.", "cloud_off")
        return
    risks = pd.DataFrame(
        [{"Risiko": label, "Wahrscheinlichkeit": p, "Treiber": ", ".join(d) or "keine besonderen"} for _, label, p, _, d in twin.risks]
    )
    bars = alt.Chart(risks).encode(
        y=alt.Y("Risiko:N", sort="-x", title=None),
        x=alt.X("Wahrscheinlichkeit:Q", axis=alt.Axis(format="%", title=None)),
        tooltip=["Risiko:N", alt.Tooltip("Wahrscheinlichkeit:Q", format=".1%"), "Treiber:N"],
    )
    chart = (
        (bars.mark_bar(color="#2a78d6", cornerRadiusTopRight=4, cornerRadiusBottomRight=4, height=18)
         + bars.mark_text(align="left", dx=6, color="#334155", font="Inter").encode(text=alt.Text("Wahrscheinlichkeit:Q", format=".1%")))
        .properties(height=150)
        .configure_axis(**AXIS)
        .configure_view(strokeWidth=0)
        .configure(background="#FFFFFF")
    )
    st.altair_chart(chart, use_container_width=True)
    events = "".join(f"<li><span>{esc(label)}</span><b>{p:.0%}</b></li>" for _, label, p in twin.events)
    render_html(f'<h4 class="dt-h4">Wahrscheinliche Lebensereignisse</h4><ul class="dt-kv">{events}</ul>')
