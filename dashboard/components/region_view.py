"""
Abschnitt im Reiter „Digital Twin“: Geo-Heatmap der Vorfälle mit Zeitschieber (Vergangenheit, heute, Prognose)
für das Bundesland des ausgewählten Kunden. Karte und Daten kommen aus geo_heatmap.py und forecast.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

from i18n import t

sys.path.append(str(Path(__file__).resolve().parents[2]))
from data_loader import load_customer  # noqa: E402
from geo_heatmap import METRIC_GROUPS, heat_points_for_step, load_disasters_df, load_incidents_df, render_heatmap  # noqa: E402
import forecast as fc  # noqa: E402

STATE_CENTERS = {
    "Baden-Württemberg": (48.66, 9.35), "Bayern": (48.95, 11.40), "Berlin": (52.52, 13.40),
    "Brandenburg": (52.45, 13.40), "Bremen": (53.08, 8.80), "Hamburg": (53.55, 10.00),
    "Hessen": (50.60, 9.00), "Mecklenburg-Vorpommern": (53.75, 12.50), "Niedersachsen": (52.75, 9.40),
    "Nordrhein-Westfalen": (51.45, 7.60), "Rheinland-Pfalz": (49.95, 7.40), "Saarland": (49.40, 6.95),
    "Sachsen": (51.05, 13.40), "Sachsen-Anhalt": (52.00, 11.70), "Schleswig-Holstein": (54.20, 9.80),
    "Thüringen": (50.90, 11.00),
}


@st.cache_data(show_spinner=False)
def _state_of(customer_id: str) -> str:
    try:
        return load_customer(customer_id).person.federal_state
    except Exception:  # noqa: BLE001
        return ""


def render_region_view(customer_id: str) -> None:
    """Heatmap mit Zeitschieber, Kennzahl-Auswahl und Prognose-Kennzahlen je Bundesland."""
    incidents, disasters = load_incidents_df(), load_disasters_df()
    if incidents.empty:
        st.info(t("region_no_data"))
        return
    home_state = _state_of(customer_id)
    regions = [t("region_all")] + fc.regions()
    default = regions.index(home_state) if home_state in regions else 0

    c1, c2, c3 = st.columns([1.2, 1.2, 2])
    region = c1.selectbox(t("region_filter"), regions, index=default, key="region_filter")
    metric = c2.selectbox(t("region_metric"), list(METRIC_GROUPS), format_func=lambda m: METRIC_GROUPS[m], key="region_metric")
    step = c3.slider(t("region_step"), -24, 12, 0, key="region_step",
                     help=t("region_step_help"))
    region_arg = None if region == t("region_all") else region
    phase = t("region_past") if step < 0 else t("region_now") if step == 0 else t("region_future", n=step)
    st.caption(f"**{fc._label(fc.LAST_MONTH, step)}** · {phase}")

    points = heat_points_for_step(incidents, metric, step, region_arg)
    nature = disasters[disasters["country"] == "DE"] if not disasters.empty else disasters
    if region_arg and not nature.empty:
        nature = nature[nature["region"] == region_arg]
    center = STATE_CENTERS.get(region_arg) if region_arg else (51.1, 10.4)
    render_heatmap(points, nature, home=None, center=center, zoom=6 if region_arg else 4.8, height=420, key="region_map")
    st.caption(t("region_map_note"))

    # Kennzahlen je Bundesland für den gewählten Monat, sortiert nach Wert
    frame = fc.heatmap_frame(metric, step)
    rows = sorted(frame.items(), key=lambda kv: kv[1], reverse=True)
    if region_arg:
        rows = [kv for kv in rows if kv[0] == region_arg] + [kv for kv in rows if kv[0] != region_arg][:3]
    cols = st.columns(min(len(rows), 4))
    for col, (state, value) in zip(cols, rows[:4]):
        col.metric(state, f"{value:.1f}", fc.trend_label(metric, state), delta_color="off")
    st.caption(t("region_kpi_note"))
