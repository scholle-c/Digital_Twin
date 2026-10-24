"""
Seitenrahmen: Sidebar (Desktop), Kopfleiste mit Suche, mobile Navigationsleiste unten.

Desktop und Mobil nutzen dieselben Streamlit-Widgets; welche Navigation sichtbar ist,
entscheidet allein das CSS über Media Queries (styles/portal.css).
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from core.state import PAGES, logout, navigate, unread_count
from ui.components import badge, esc, icon, logo_html, render_html


# Bindet das zentrale Stylesheet ein.
def load_css(path: Path) -> None:
    """Liest styles/portal.css und fügt es in die Seite ein."""
    st.markdown(f"<style>{path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


# Desktop-Navigation in der Sidebar: Logo, alle Seiten, Abmelden.
def render_sidebar(active: str) -> None:
    """Rendert die linke Navigation mit hervorgehobener aktiver Seite."""
    unread = unread_count()
    with st.sidebar:
        render_html(logo_html())
        with st.container(key="side_nav"):
            for page, (title, sym) in PAGES.items():
                label = f"{title} ({unread})" if page == "notifications" and unread else title
                st.button(
                    label, key=f"nav_{page}", icon=f":material/{sym}:", on_click=navigate, args=(page,),
                    type="primary" if page == active else "secondary",
                )
        with st.container(key="side_foot"):
            render_html(f'<div class="dt-side-note">{icon("lock", "ms-sm")}Demo-Sitzung · keine echten Daten</div>')
            st.button("Abmelden", key="nav_logout", icon=":material/logout:", on_click=logout)


# Kopfleiste: Suche, Mitteilungen und Kundenprofil. Auf dem Handy kompakt mit Logo.
def render_topbar(profile: dict) -> None:
    """Rendert die obere Leiste mit Suche, Glocke und Profilzugang."""
    unread = unread_count()
    with st.container(key="topbar"):
        render_html(f'<div class="dt-mobile-logo">{logo_html(compact=True)}</div>')
        search_col, bell_col, user_col = st.columns([6, 1.1, 2.4], vertical_alignment="center")
        with search_col:
            st.text_input(
                "Suche", key="search_query", placeholder="Suchen: Verträge, Angebote, Seiten …",
                label_visibility="collapsed",
            )
        with bell_col:
            st.button(
                str(unread), key="top_bell", icon=":material/notifications:",
                help="Mitteilungen", on_click=navigate, args=("notifications",),
            )
        with user_col:
            st.button(
                f"{profile['first_name']} {profile['last_name']}", key="top_user", icon=":material/account_circle:",
                help="Mein Profil", on_click=navigate, args=("profile",),
            )


# Suchtreffer über Seiten, Verträge und Angebote; Klick navigiert direkt dorthin.
def render_search_results(query: str, policies: list, offers: list) -> None:
    """Zeigt Treffer zur Suchanfrage oder einen Leerzustand."""
    q = query.strip().lower()
    if not q:
        return
    hits = [(title, page, "Seite") for page, (title, _) in PAGES.items() if q in title.lower()]
    hits += [(p.name, "insurance", "Vertrag") for p in policies if q in f"{p.name} {p.product_line}".lower()]
    hits += [(o.product.name, "offers", "Angebot") for o in offers if q in o.product.name.lower()]
    with st.container(key="search_results"):
        if not hits:
            render_html(f'<div class="dt-muted">Keine Treffer für „{esc(query)}“.</div>')
            return
        render_html(f'<div class="dt-muted">{len(hits)} Treffer</div>')
        for index, (title, page, kind) in enumerate(hits[:8]):
            st.button(f"{title} · {kind}", key=f"hit_{index}", on_click=navigate, args=(page,), icon=":material/arrow_forward:")


# Mobile Navigationsleiste unten (per CSS nur auf schmalen Bildschirmen sichtbar).
MOBILE_ITEMS = [("home", "Start", "home"), ("insurance", "Verträge", "verified_user"),
                ("offers", "Angebote", "local_offer"), ("questionnaire", "Umfragen", "assignment")]


def render_bottom_nav(active: str) -> None:
    """Rendert die Tab-Leiste für Mobilgeräte inklusive „Mehr“-Menü."""
    with st.container(key="bottom_nav"):
        columns = st.columns(len(MOBILE_ITEMS) + 1)
        for column, (page, label, sym) in zip(columns, MOBILE_ITEMS):
            with column:
                st.button(
                    label, key=f"bn_{page}", icon=f":material/{sym}:", on_click=navigate, args=(page,),
                    type="primary" if page == active else "secondary",
                )
        with columns[-1]:
            with st.popover(":material/menu: Mehr"):
                for page in ("profile", "trends", "notifications", "settings"):
                    title, sym = PAGES[page]
                    st.button(title, key=f"bn_more_{page}", icon=f":material/{sym}:", on_click=navigate,
                              args=(page,))
                st.button("Abmelden", key="bn_logout", icon=":material/logout:", on_click=logout)


# Kleine Kopfzeile einer Karte: Titel links, Status oder Link rechts.
def card_head(title: str, right_html: str = "") -> None:
    """Rendert die Kopfzeile einer Inhaltskarte."""
    render_html(f'<div class="dt-card-head"><h3 class="dt-h3">{esc(title)}</h3>{right_html}</div>')


# Hilfsfunktion für Status-Badges von Verträgen.
def policy_badge(status: str, labels: dict) -> str:
    """Gibt das Badge für einen Vertragsstatus zurück."""
    label, sym, tone = labels[status]
    return badge(label, tone, sym)
