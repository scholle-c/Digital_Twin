"""
Allianz Digital Twin – Kundenportal (Streamlit-Prototyp).

Start:  streamlit run app.py   (im Ordner customer_portal/)

Aufbau:
    core/data.py             Demodaten, Verträge, CSV-Loader, Mitteilungen
    core/twin.py             Anbindung an digital_twin.py + config.toml des Projekts
    core/personalization.py  Absicherungsgrad und Angebote
    core/state.py            Sitzungszustand, Login, Navigation, Aktionen
    ui/components.py         Designsystem (Karten, Badges, Ring, Leerzustände)
    ui/layout.py             Sidebar, Kopfleiste, Suche, mobile Navigation
    views/*.py               eine Datei pro Seite
    styles/portal.css        Design-Tokens, Layout, Responsive-Regeln
"""
from pathlib import Path

import streamlit as st

from core.personalization import build_offers, coverage_needs, coverage_score, current_twin, customer_facts
from core.state import PAGES, init_state
from ui.components import prototype_notice
from ui.layout import load_css, render_bottom_nav, render_search_results, render_sidebar, render_topbar
from views import dashboard, insurance, login, notifications, offers, profile, questionnaire, settings, trends

# Seitenkonfiguration: breites Layout, Sidebar geöffnet (auf dem Handy blendet CSS sie aus).
st.set_page_config(page_title="Allianz Digital Twin – Kundenportal", page_icon="🛡️", layout="wide",
                   initial_sidebar_state="expanded")
load_css(Path(__file__).parent / "styles" / "portal.css")
init_state()

# Ohne Anmeldung nur die Login-Seite.
if not st.session_state.authenticated:
    login.render()
    st.stop()


# Bündelt alles, was die Seiten zum Rendern brauchen. Wird bei jedem Rerun neu berechnet,
# daher wirken Profil- und Fragebogenänderungen sofort auf Dashboard und Angebote.
def build_context() -> dict:
    """Berechnet Twin-Ergebnis, Absicherungsgrad und Angebote für den aktuellen Stand."""
    profile, policies = st.session_state.profile, st.session_state.policies
    facts = customer_facts(profile, st.session_state.answers)
    personalized = st.session_state.consents["personalization"]
    twin = current_twin(policies, facts, profile["customer_id"]) if personalized else None
    needs = coverage_needs(policies, facts, twin)
    offers_all = build_offers(policies, facts, twin) if personalized else []
    return {
        "profile": profile, "policies": policies, "facts": facts, "twin": twin, "needs": needs,
        "score": coverage_score(needs), "personalized": personalized,
        "offers": [o for o in offers_all if o.product.id not in st.session_state.dismissed_offers],
    }


with st.spinner("Ihr Digital Twin wird berechnet …"):
    ctx = build_context()
page = st.session_state.page if st.session_state.page in PAGES else "home"

# Kurze Bestätigungen aus Callbacks einmalig anzeigen.
if st.session_state.toast:
    st.toast(st.session_state.toast, icon="✅")
    st.session_state.toast = None

# Seitenrahmen: Navigation (Desktop links, Mobil unten), Kopfleiste mit Suche, Prototyp-Hinweis.
render_sidebar(page)
render_topbar(ctx["profile"])
render_search_results(st.session_state.get("search_query", ""), ctx["policies"], ctx["offers"])
prototype_notice()

VIEWS = {
    "home": dashboard, "profile": profile, "insurance": insurance, "offers": offers,
    "questionnaire": questionnaire, "trends": trends, "notifications": notifications, "settings": settings,
}
VIEWS[page].render(ctx)
render_bottom_nav(page)
