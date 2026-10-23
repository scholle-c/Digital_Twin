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

from i18n import t
from state import select_customer

sys.path.append(str(Path(__file__).resolve().parents[2]))
from twin_comparison import Portfolio, build_portfolio, damage_rank, nearest, percentile  # noqa: E402

HIGHLIGHT = "#1f4e8c"
NEIGHBOR = "#e8a33d"
BUILDING_TYPES = {
    "apartment": "Wohnung",
    "semi_detached": "Doppelhaushälfte",
    "terraced_house": "Reihenhaus",
    "detached_house": "Einfamilienhaus",
}


@st.cache_data(ttl=10, show_spinner=False)
def _portfolio() -> Portfolio:
    return build_portfolio()


def render_twin_comparison(customer_id: str) -> None:
    """Kennzahlen, Position im Bestand, Twin-Landkarte und ähnlichste Twins."""
    portfolio = _portfolio()
    if customer_id not in portfolio.snapshots:
        st.info(t("not_specified"))
        return
    neighbors = nearest(portfolio, customer_id, k=5)

    st.subheader(t("twin_heading", n=len(portfolio.ids) - 1))
    _render_kpis(portfolio, customer_id, neighbors)

    st.markdown(f"**{t('twin_position')}**")
    st.plotly_chart(_position_chart(portfolio, customer_id), width="stretch", key="twin_position_chart")
    st.caption(t("twin_position_note"))

    st.markdown(f"**{t('twin_map')}**")
    color_metric = st.selectbox(t("twin_color_by"), list(portfolio.metric_groups), key="twin_color_metric")
    st.plotly_chart(_map_chart(portfolio, customer_id, neighbors, color_metric), width="stretch", key="twin_map_chart")
    st.caption(t("twin_map_note"))

    st.markdown(f"**{t('twin_neighbors')}**")
    _render_neighbors(portfolio, neighbors)


def _render_kpis(portfolio: Portfolio, customer_id: str, neighbors: list[tuple[str, float]]) -> None:
    snapshot = portfolio.snapshots[customer_id]
    percentiles = {m: percentile(portfolio, customer_id, m) for m in portfolio.metric_groups}
    outlier = max(percentiles, key=percentiles.get)
    first, second, third = st.columns(3)
    first.metric(t("twin_most_similar"), f"{neighbors[0][0]} · {neighbors[0][1]:.0%}")
    second.metric(
        t("twin_damage"),
        f"{snapshot.expected_damage_eur:,.0f} €".replace(",", "."),
        t("twin_damage_rank", rank=damage_rank(portfolio, customer_id), n=len(portfolio.ids)),
        delta_color="off",
    )
    third.metric(t("twin_outlier"), outlier, t("twin_outlier_value", p=percentiles[outlier]), delta_color="off")


def _position_chart(portfolio: Portfolio, customer_id: str) -> go.Figure:
    groups = list(dict.fromkeys(portfolio.metric_groups.values()))
    figure = make_subplots(
        rows=len(groups), cols=1, subplot_titles=groups, vertical_spacing=0.18,
        row_heights=[sum(g == group for g in portfolio.metric_groups.values()) for group in groups],
    )
    others = [i for i, cid in enumerate(portfolio.ids) if cid != customer_id]
    for row, group in enumerate(groups, start=1):
        metrics = [m for m, g in portfolio.metric_groups.items() if g == group]
        for y, metric in enumerate(metrics):
            values = portfolio.values(metric) * 100
            mine = portfolio.snapshots[customer_id].metrics[metric] * 100
            first = row == 1 and y == 0
            figure.add_trace(
                go.Scatter(
                    x=values[others], y=[metric] * len(others),
                    mode="markers",
                    marker={"color": "rgba(120,120,120,0.35)", "size": 7},
                    text=[portfolio.ids[i] for i in others],
                    hovertemplate="%{text}: %{x:.1f} %<extra></extra>",
                    name=t("twin_others"), legendgroup="others", showlegend=first,
                ),
                row=row, col=1,
            )
            figure.add_trace(
                go.Scatter(
                    x=[float(np.median(values))], y=[metric], mode="markers",
                    marker={"symbol": "line-ns-open", "size": 22, "color": "#444", "line": {"width": 2}},
                    hovertemplate=t("twin_median") + ": %{x:.1f} %<extra></extra>",
                    name=t("twin_median"), legendgroup="median", showlegend=first,
                ),
                row=row, col=1,
            )
            figure.add_trace(
                go.Scatter(
                    x=[mine], y=[metric], mode="markers",
                    marker={"size": 15, "color": HIGHLIGHT, "line": {"color": "white", "width": 2}},
                    hovertemplate=f"{customer_id}: %{{x:.1f}} % · P{percentile(portfolio, customer_id, metric)}<extra></extra>",
                    name=customer_id, legendgroup="me", showlegend=first,
                ),
                row=row, col=1,
            )
        figure.update_xaxes(ticksuffix=" %", row=row, col=1)
        figure.update_yaxes(autorange="reversed", row=row, col=1)
    figure.update_layout(
        height=110 + 45 * len(portfolio.metric_groups),
        margin={"l": 10, "r": 10, "t": 40, "b": 10},
        legend={"orientation": "h", "y": -0.08},
        plot_bgcolor="white",
    )
    figure.update_xaxes(showgrid=True, gridcolor="#eee")
    return figure


def _map_chart(
    portfolio: Portfolio, customer_id: str, neighbors: list[tuple[str, float]], color_metric: str
) -> go.Figure:
    coords = portfolio.coords
    index = {cid: i for i, cid in enumerate(portfolio.ids)}
    values = portfolio.values(color_metric) * 100
    me = index[customer_id]
    hover = [
        f"{cid} · {portfolio.snapshots[cid].city or '–'}<br>{portfolio.snapshots[cid].age_group} · "
        f"{BUILDING_TYPES.get(portfolio.snapshots[cid].building_type, portfolio.snapshots[cid].building_type)}<br>"
        f"{color_metric}: {values[i]:.1f} %"
        for i, cid in enumerate(portfolio.ids)
    ]

    figure = go.Figure()
    for neighbor_id, similarity in neighbors:
        n = index[neighbor_id]
        figure.add_trace(
            go.Scatter(
                x=[coords[me, 0], coords[n, 0]], y=[coords[me, 1], coords[n, 1]], mode="lines",
                line={"color": NEIGHBOR, "width": 1 + 3 * similarity, "dash": "dot"},
                hoverinfo="skip", showlegend=False,
            )
        )
    figure.add_trace(
        go.Scatter(
            x=coords[:, 0], y=coords[:, 1], mode="markers",
            marker={
                "size": 11, "color": values, "colorscale": "YlOrRd", "cmin": 0,
                "colorbar": {"title": {"text": "%"}, "thickness": 12},
                "line": {"color": "white", "width": 1},
            },
            text=hover, hovertemplate="%{text}<extra></extra>", name=t("twin_others"),
        )
    )
    neighbor_rows = [index[nid] for nid, _ in neighbors]
    figure.add_trace(
        go.Scatter(
            x=coords[neighbor_rows, 0], y=coords[neighbor_rows, 1], mode="markers+text",
            marker={"size": 17, "color": "rgba(0,0,0,0)", "line": {"color": NEIGHBOR, "width": 2.5}},
            text=[nid for nid, _ in neighbors], textposition="top center", textfont={"size": 10},
            hoverinfo="skip", name=t("twin_neighbors"),
        )
    )
    figure.add_trace(
        go.Scatter(
            x=[coords[me, 0]], y=[coords[me, 1]], mode="markers+text",
            marker={"size": 22, "symbol": "star", "color": HIGHLIGHT, "line": {"color": "white", "width": 1.5}},
            text=[customer_id], textposition="bottom center", textfont={"color": HIGHLIGHT},
            hovertext=[hover[me]], hovertemplate="%{hovertext}<extra></extra>", name=customer_id,
        )
    )
    figure.update_xaxes(visible=False)
    figure.update_yaxes(visible=False)
    figure.update_layout(
        height=480, margin={"l": 10, "r": 10, "t": 10, "b": 10},
        legend={"orientation": "h", "y": -0.02}, plot_bgcolor="#fafafa",
    )
    return figure


def _render_neighbors(portfolio: Portfolio, neighbors: list[tuple[str, float]]) -> None:
    metrics = list(portfolio.metric_groups)
    rows = []
    for neighbor_id, similarity in neighbors:
        snapshot = portfolio.snapshots[neighbor_id]
        rows.append(
            {
                "Kunde": neighbor_id,
                "Ähnlichkeit": f"{similarity:.0%}",
                "Ort": snapshot.city or "–",
                "Alter": snapshot.age_group,
                "Gebäude": BUILDING_TYPES.get(snapshot.building_type, snapshot.building_type),
                "Life Events": ", ".join(snapshot.life_events) or "–",
                "Top-Empfehlung": snapshot.top_recommendation or "–",
                **{m: f"{snapshot.metrics[m]:.0%}" for m in metrics},
            }
        )
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    for column, (neighbor_id, _) in zip(st.columns(len(neighbors)), neighbors):
        column.button(
            t("twin_open", id=neighbor_id),
            key=f"twin_open_{neighbor_id}",
            on_click=select_customer,
            args=(neighbor_id,),
            width="stretch",
        )
