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

HIGHLIGHT = "#003781"
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
    st.plotly_chart(
        _position_chart(portfolio, customer_id), width="stretch", key="twin_position_chart",
        theme=None, config={"displayModeBar": False, "scrollZoom": False},
    )
    st.caption(t("twin_position_note"))

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
                marker={"color": "#DCE4EF", "cornerradius": 4},
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
                    "%{y}<br>" + customer_id + ": %{x:.1f} %<br>"
                    + t("twin_outlier_value", p="%{customdata}") + "<extra></extra>"
                ),
                name=customer_id, legendgroup="me", showlegend=row == 1,
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
        margin={"l": 10, "r": 45, "t": 45, "b": 45},
        legend={"orientation": "h", "y": -0.12, "traceorder": "reversed", "font": {"size": 11}},
        font={"family": "Inter, sans-serif", "color": "#1E293B", "size": 12},
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    figure.update_annotations(font={"size": 12, "color": "#5B6B82"}, x=0, xanchor="left")
    figure.update_xaxes(showgrid=True, gridcolor="#DCE4EF", zeroline=False, fixedrange=True, tickfont={"size": 10})
    figure.update_yaxes(tickfont={"size": 11}, fixedrange=True, automargin=True)
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
