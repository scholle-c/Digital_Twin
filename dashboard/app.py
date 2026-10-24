"""
Customer 360 – Beratungscockpit für Versicherungsberater (Streamlit-Prototyp).

Start:  streamlit run app.py   (im Ordner dashboard/)

Aufbau:
    data/twin_data.py              Kundendaten aus den Digital Twins (Quelle: data_loader)
    data/mock_data.py              Datenmodell (und frühere synthetische Kundendaten)
    state.py                       st.session_state und Klick-Callbacks
    components/layout.py           CSS, Navigation, Kopfbereich
    components/customer_list.py    priorisierte Kundenliste
    components/customer_detail.py  Detailansicht, Empfehlung, Absicherung, Timeline
    components/coverage_detail.py  Versicherungsdetailseite mit Prognosen und Empfehlung
    styles/dashboard.css           Design-Tokens und Layout
"""
from pathlib import Path

import streamlit as st

from components.coverage_detail import render_coverage_page
from components.customer_detail import render_customer_detail
from components.customer_list import render_customer_list
from components.layout import load_css, render_header, render_sidebar
from components.region_view import render_region_view
from data.twin_data import get_customers, prioritized_demo_customers
from data.mock_data import ADVISOR
from i18n import t
from state import VIEW_COVERAGE, init_session_state

# 1. Seitenkonfiguration: breites Dashboard-Layout, Sidebar dauerhaft geöffnet.
st.set_page_config(
    page_title="Customer 360 – Übersicht",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 2. Zentrales CSS mit Design-Tokens laden (Farben, Karten, Klick-Overlays).
load_css(Path(__file__).parent / "styles" / "dashboard.css")

if st.session_state.get("region_fullscreen") and st.session_state.get("selected_customer_id"):
    with st.container(key="region_presentation"):
        render_region_view(st.session_state.selected_customer_id, fullscreen=True)
    st.stop()

# 3. Kunden aus ihren Digital Twins laden; die Liste ist bereits fachlich priorisiert.
customers = get_customers()
# Demo: nur die wichtigsten Kunden auflisten; Auswahl und Twin-Vergleich nutzen weiter alle.
PRIORITY_LIST_SIZE = 5
prioritized_customers = prioritized_demo_customers(customers, limit=PRIORITY_LIST_SIZE)

# 4. Sitzungszustand initialisieren; standardmäßig ist der wichtigste Kunde ausgewählt.
init_session_state(default_customer_id=customers[0].id)
selected_customer = next(
    (c for c in customers if c.id == st.session_state.selected_customer_id), customers[0]
)
selected_coverage = next(
    (c for c in selected_customer.coverages if c.key == st.session_state.selected_coverage), None
)

# 5. Kurze Bestätigungen aus Callbacks (z. B. „Erinnerung gesetzt“) einmalig anzeigen.
if st.session_state.pending_toast:
    st.toast(t(st.session_state.pending_toast), icon="✅")
    st.session_state.pending_toast = None

# 6a. Versicherungsdetailseite, wenn eine Versicherung angeklickt wurde.
if st.session_state.view == VIEW_COVERAGE and selected_coverage is not None:
    render_sidebar(active="nav_customers")
    render_coverage_page(selected_customer, selected_coverage, ADVISOR)

# 6b. Sonst die Übersicht: links die priorisierte Kundenliste, rechts die Details zum Kunden.
else:
    render_sidebar(active="nav_overview")
    render_header(ADVISOR, open_customers=len(prioritized_customers))
    with st.container(key="workspace"):
        list_column, detail_column = st.columns([1, 2.6], gap="large")
        with list_column:
            render_customer_list(prioritized_customers, selected_customer.id)
        with detail_column:
            render_customer_detail(selected_customer)
