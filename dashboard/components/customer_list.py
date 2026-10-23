"""
Priorisierte Kundenliste (linke Spalte des Inhaltsbereichs).

Jede Karte besteht aus HTML für die Optik und einem unsichtbaren Streamlit-Button,
der per CSS über die gesamte Karte gelegt wird. So ist die ganze Karte klickbar
und die Auswahl läuft trotzdem über st.session_state.
"""
from __future__ import annotations

import streamlit as st

from components.ui import category_class, esc, icon, render_html
from data.mock_data import CATEGORIES, Customer
from i18n import t
from state import select_customer


# Rendert den Kartencontainer „Priorisierte Kunden“ mit allen Kundenkarten.
def render_customer_list(customers: list[Customer], selected_id: str) -> None:
    """Zeigt die bereits sortierte Kundenliste und markiert den ausgewählten Kunden."""
    with st.container(key="panel_list"):
        render_html(
            f'<div class="c360-panel-title c360-list-heading" role="heading" aria-level="2">'
            f'{t("prioritized_customers")}<span class="c360-count">{len(customers)}</span></div>'
        )
        with st.container(key="customer_queue"):
            for rank, customer in enumerate(customers, start=1):
                render_customer_card(customer, rank, customer.id == selected_id)


# Eine einzelne, anklickbare Kundenkarte mit Rang, Kategorie, Frist und Begründung.
def render_customer_card(customer: Customer, rank: int, is_selected: bool) -> None:
    """Rendert eine Kundenkarte; ein Klick wählt den Kunden über select_customer aus."""
    category = CATEGORIES[customer.category]
    selected_class = " is-selected" if is_selected else ""
    with st.container(key=f"custcard_{customer.id}"):
        render_html(
            f"""
            <div class="c360-cust-card {category_class(customer.category)}{selected_class}">
                <div class="c360-cust-top">
                    <span class="c360-rank" aria-label="{t("rank", n=rank)}">{rank}</span>
                    <span class="c360-cust-name">{esc(customer.name)}</span>
                    {icon("chevron_right", "c360-icon c360-chevron")}
                </div>
                <div class="c360-cust-body">
                    <span class="c360-icon-circle">{icon(customer.topic_icon)}</span>
                    <div>
                        <div class="c360-tags">
                            <span class="c360-tag">{esc(category.label)}</span>
                            <span class="c360-due">{esc(customer.urgency)}</span>
                        </div>
                        <div class="c360-reason">{esc(customer.reason)}</div>
                    </div>
                </div>
            </div>
            """
        )
        st.button(
            t("open_customer", name=customer.name),
            key=f"custpick_{customer.id}",
            on_click=select_customer,
            args=(customer.id,),
        )
