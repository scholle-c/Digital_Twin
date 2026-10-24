"""
Reiter „Digital Twin“: der Twin des ausgewählten Kunden im Vergleich zu allen anderen Twins.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from components.region_view import render_region_view
from components.ui import esc, icon, render_html
from data.twin_data import get_customers
from i18n import t, tr
from state import select_customer

sys.path.append(str(Path(__file__).resolve().parents[2]))
from twin_comparison import Portfolio, build_portfolio, damage_rank, nearest, percentile  # noqa: E402

HIGHLIGHT = "#003781"
BUILDING_TYPES = {
    "apartment": "Wohnung",
    "semi_detached": "Doppelhaushälfte",
    "terraced_house": "Reihenhaus",
    "detached_house": "Einfamilienhaus",
}


# Das Portfolio wird nur neu berechnet, wenn sich eine CSV in generated_demodata ändert
# (vorher: alle 10 s, bei 250 Kunden ein Dauer-Lag von 40+ s).
def _data_stamp() -> float:
    folder = Path(__file__).resolve().parents[2] / "generated_demodata"
    return max((f.stat().st_mtime for f in folder.glob("*.csv")), default=0.0)


@st.cache_data(show_spinner="Digital Twins werden berechnet …")
def _portfolio(stamp: float) -> Portfolio:
    return build_portfolio()


def render_twin_comparison(customer_id: str) -> None:
    """Kennzahlen, Position im Bestand, Twin-Landkarte und ähnlichste Twins."""
    portfolio = _portfolio(_data_stamp())
    if customer_id not in portfolio.snapshots:
        st.info(t("not_specified"))
        return
    neighbors = nearest(portfolio, customer_id, k=5)
    names = {customer.id: customer.name for customer in get_customers()}

    render_html(
        f'<div class="c360-twin-heading"><div><span class="c360-twin-eyebrow">'
        f'{esc(t("twin_analysis"))}</span><h3>{esc(t("twin_position"))}</h3></div>'
        f'<span class="c360-twin-count">{icon("users")} {esc(t("twin_population", n=len(portfolio.ids)))}</span></div>'
    )
    with st.container(key="twin_kpis"):
        _render_kpis(portfolio, customer_id, neighbors, names)

    with st.container(key="twin_sections"):
        profile, regional, similar = st.tabs([
            f":material/monitoring: {t('twin_profile_tab')}",
            f":material/map: {t('twin_region_tab')}",
            f":material/groups: {t('twin_similar_tab')}",
        ])
        with profile:
            st.caption(t("twin_position_note"))
            st.plotly_chart(
                _position_chart(portfolio, customer_id, names[customer_id]), width="stretch", key="twin_position_chart",
                theme=None, config={"displayModeBar": False, "scrollZoom": False},
            )
        with regional:
            render_region_view(customer_id)
        with similar:
            render_html(
                f'<div class="c360-twin-section-title"><h4>{esc(t("twin_neighbors"))}</h4>'
                f'<span>{esc(t("twin_neighbor_count", n=len(neighbors)))}</span></div>'
            )
            _render_neighbors(portfolio, neighbors, names)


def _render_kpis(portfolio: Portfolio, customer_id: str, neighbors: list[tuple[str, float]], names: dict[str, str]) -> None:
    snapshot = portfolio.snapshots[customer_id]
    percentiles = {m: percentile(portfolio, customer_id, m) for m in portfolio.metric_groups}
    outlier = max(percentiles, key=percentiles.get)
    first, second, third = st.columns(3)
    first.metric(
        t("twin_damage"),
        f"{snapshot.expected_damage_eur:,.0f} €".replace(",", "."),
        t("twin_damage_rank", rank=damage_rank(portfolio, customer_id), n=len(portfolio.ids)),
        delta_color="off",
    )
    second.metric(t("twin_outlier"), tr(outlier), t("twin_outlier_value", p=percentiles[outlier]), delta_color="off")
    with third.container(key="twin_identity"):
        if neighbors:
            st.metric(t("twin_most_similar"), names[neighbors[0][0]],
                      f"{neighbors[0][0]} · {neighbors[0][1]:.0%}", delta_color="off")
        else:
            st.metric(t("twin_most_similar"), t("not_specified"))


def _position_chart(portfolio: Portfolio, customer_id: str, customer_name: str) -> go.Figure:
    groups = list(dict.fromkeys(portfolio.metric_groups.values()))
    figure = make_subplots(
        rows=len(groups), cols=1, subplot_titles=groups, vertical_spacing=0.16,
        row_heights=[sum(g == group for g in portfolio.metric_groups.values()) for group in groups],
    )
    for row, group in enumerate(groups, start=1):
        metrics = [m for m, g in portfolio.metric_groups.items() if g == group]
        mine = [portfolio.snapshots[customer_id].metrics[m] * 100 for m in metrics]
        average = [float(np.mean(portfolio.values(m))) * 100 for m in metrics]
        ranks = [percentile(portfolio, customer_id, m) for m in metrics]
        figure.add_trace(
            go.Bar(
                y=metrics, x=average, orientation="h",
                marker={"color": "#B7C7DA", "cornerradius": 4},
                text=[f"{v:.1f} %" for v in average], textposition="outside",
                textfont={"color": "#5B6B82", "size": 11}, cliponaxis=False,
                hovertemplate="%{y}<br>" + t("twin_average") + ": %{x:.1f} %<extra></extra>",
                name=t("twin_average"), legendgroup="average", showlegend=row == 1,
            ),
            row=row, col=1,
        )
        figure.add_trace(
            go.Bar(
                y=metrics, x=mine, orientation="h",
                marker={"color": HIGHLIGHT, "cornerradius": 4},
                text=[f"<b>{v:.1f} %</b>" for v in mine], textposition="outside", cliponaxis=False,
                textfont={"color": HIGHLIGHT, "size": 12},
                customdata=ranks,
                hovertemplate=(
                    "%{y}<br>" + customer_name + ": %{x:.1f} %<br>" + customer_id + "<br>"
                    + t("twin_outlier_value", p="%{customdata}") + "<extra></extra>"
                ),
                name=customer_name, legendgroup="me", showlegend=row == 1,
            ),
            row=row, col=1,
        )
        figure.update_xaxes(
            ticksuffix=" %", range=[0, max(mine + average) * 1.35 or 1], row=row, col=1
        )
        figure.update_yaxes(autorange="reversed", row=row, col=1)
    figure.update_layout(
        barmode="group", bargap=0.35, bargroupgap=0.08,
        height=130 + 62 * len(portfolio.metric_groups),
        margin={"l": 10, "r": 45, "t": 90, "b": 30},
        legend={"orientation": "h", "y": 1.18, "x": 0, "traceorder": "reversed", "font": {"size": 11}},
        font={"family": "Inter, sans-serif", "color": "#1E293B", "size": 12},
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    figure.update_annotations(font={"size": 12, "color": "#5B6B82"}, x=0, xanchor="left")
    figure.update_xaxes(showgrid=True, gridcolor="#DCE4EF", zeroline=False, fixedrange=True, tickfont={"size": 10})
    figure.update_yaxes(tickfont={"size": 11}, fixedrange=True, automargin=True)
    return figure


def _render_neighbors(portfolio: Portfolio, neighbors: list[tuple[str, float]], names: dict[str, str]) -> None:
    if not neighbors:
        st.info(t("not_specified"))
        return
    for start in range(0, len(neighbors), 2):
        columns = st.columns(2, gap="small")
        for column, (neighbor_id, similarity) in zip(columns, neighbors[start:start + 2]):
            snapshot = portfolio.snapshots[neighbor_id]
            rank = next(index for index, entry in enumerate(neighbors, start=1) if entry[0] == neighbor_id)
            initials = "".join(part[0] for part in names[neighbor_id].split()[:2])
            with column.container(key=f"twin_neighbor_{neighbor_id}"):
                render_html(
                    f'<div class="c360-twin-neighbor{" is-closest" if rank == 1 else ""}">'
                    f'<div class="c360-twin-neighbor-top"><span class="c360-twin-initials">{esc(initials)}</span>'
                    f'<div class="c360-twin-person"><strong>{esc(names[neighbor_id])}</strong>'
                    f'<small>{esc(neighbor_id)}</small></div>'
                    f'<span class="c360-twin-match"><strong>{similarity:.0%}</strong>'
                    f'<small>{esc(t("twin_similarity"))}</small></span></div>'
                    f'<meter class="c360-twin-meter" min="0" max="1" value="{similarity:.4f}" '
                    f'aria-label="{esc(t("twin_similarity"))}">{similarity:.0%}</meter>'
                    f'<div class="c360-twin-facts"><span>{icon("map_pin", "c360-icon c360-icon-xs")}'
                    f'{esc(snapshot.city or t("not_specified"))}</span><span>{esc(snapshot.age_group)} '
                    f'{esc(t("twin_years"))}</span></div>'
                    f'<div class="c360-twin-housing">{esc(tr(BUILDING_TYPES.get(snapshot.building_type, snapshot.building_type)))}</div>'
                    f'<div class="c360-twin-neighbor-footer"><span>{esc(t("twin_open_profile"))}</span>'
                    f'{icon("chevron_right", "c360-icon c360-icon-sm")}</div></div>'
                )
                st.button(
                    t("twin_open", name=names[neighbor_id]), key=f"twin_open_{neighbor_id}",
                    help=t("twin_open", name=names[neighbor_id]),
                    on_click=select_customer, args=(neighbor_id,), width="stretch",
                )
    metrics = list(portfolio.metric_groups)
    rows = []
    for neighbor_id, similarity in neighbors:
        snapshot = portfolio.snapshots[neighbor_id]
        rows.append(
            {
                "Kunde": names[neighbor_id],
                "ID": neighbor_id,
                "Ähnlichkeit": f"{similarity:.0%}",
                "Ort": snapshot.city or "–",
                "Alter": snapshot.age_group,
                "Gebäude": BUILDING_TYPES.get(snapshot.building_type, snapshot.building_type),
                "Life Events": ", ".join(snapshot.life_events) or "–",
                "Top-Empfehlung": snapshot.top_recommendation or "–",
                **{m: f"{snapshot.metrics[m]:.0%}" for m in metrics},
            }
        )
    with st.expander(t("twin_comparison_details"), icon=":material/table_chart:"):
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
