"""
Seitenrahmen des Dashboards: zentrales CSS, linke Navigation mit Sprachumschalter
und Kopfbereich.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import streamlit as st

from components.ui import esc, icon, render_html
from i18n import t
from state import toggle_language


# Lädt die zentrale CSS-Datei und bindet sie einmal pro Rerun in die Seite ein.
# Alle Farben und Abstände stehen als Design-Tokens in styles/dashboard.css.
def load_css(css_path: Path) -> None:
    """Liest die CSS-Datei ein und fügt sie als <style>-Block in die Seite ein."""
    css = css_path.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


# Navigationseinträge der linken Leiste (Symbol, Textschlüssel aus i18n). Weitere
# Seiten können später über st.navigation angebunden werden.
NAV_ITEMS = [
    ("home", "nav_overview"),
    ("users", "nav_customers"),
    ("tasks", "nav_tasks"),
]


# Wort-Bild-Marke wie im Kundenportal (kein offizielles Allianz-Logo).
def logo_html() -> str:
    """Gibt die Marke „Allianz Digital Twin“ mit Untertitel für das Beratercockpit zurück."""
    mark = (
        '<svg class="c360-logo-mark" viewBox="0 0 40 40" aria-hidden="true">'
        '<rect width="40" height="40" rx="11" fill="#003781"/>'
        '<circle cx="16" cy="20" r="8.5" fill="none" stroke="#fff" stroke-width="3"/>'
        '<circle cx="24" cy="20" r="8.5" fill="none" stroke="#7FC4FD" stroke-width="3"/></svg>'
    )
    return (
        f'<div class="c360-logo">{mark}<div><span class="c360-logo-word">Allianz <b>Digital Twin</b></span>'
        f'<span class="c360-logo-sub">{t("logo_sub")}</span></div></div>'
    )


# Zeichnet die schmale Navigation in der Streamlit-Sidebar, hebt den aktiven Bereich
# hervor und zeigt darunter den Sprachumschalter Deutsch/Englisch.
def render_sidebar(active: str = "nav_overview") -> None:
    """Rendert die linke Navigation; "active" ist der Textschlüssel des aktiven Eintrags."""
    items = ""
    for icon_name, label_key in NAV_ITEMS:
        state = ' is-active" aria-current="page' if label_key == active else ""
        items += f'<div class="c360-nav-item{state}">{icon(icon_name)}<span>{t(label_key)}</span></div>'
    with st.sidebar:
        render_html(logo_html())
        render_html(f'<nav class="c360-nav" aria-label="{t("nav_aria")}">{items}</nav>')
        # Der Button zeigt immer die Zielsprache an, z. B. „English“, solange Deutsch aktiv ist.
        st.button(
            t("lang_switch"),
            key="lang_toggle",
            icon=":material/translate:",
            help=t("lang_switch_help"),
            on_click=toggle_language,
        )
    with st.container(key="mobile_header"):
        brand, language = st.columns([4, 1], vertical_alignment="center")
        with brand:
            render_html(logo_html())
        with language:
            st.button(
                t("lang_switch"), key="mobile_lang_toggle", icon=":material/translate:",
                help=t("lang_switch_help"), on_click=toggle_language,
            )


# Wählt die Begrüßung passend zur Tageszeit.
def _greeting() -> str:
    """Gibt die Begrüßung für Morgen, Tag oder Abend in der aktiven Sprache zurück."""
    hour = datetime.now().hour
    if hour < 11:
        return t("greeting_morning")
    if hour < 18:
        return t("greeting_day")
    return t("greeting_evening")


# Kopfbereich mit Begrüßung, Anzahl offener Kunden, Benachrichtigungen und Benutzer.
def render_header(advisor: dict[str, str], open_customers: int) -> None:
    """Rendert die Begrüßung des Beraters sowie Benachrichtigungs- und Benutzerbereich."""
    name = esc(advisor["first_name"])
    subline = t("subline_one") if open_customers == 1 else t("subline_many", n=open_customers)
    render_html(
        f"""
        <div class="c360-header">
            <div>
                <div class="c360-workspace-label">{t("workspace_label")}</div>
                <div class="c360-greeting" role="heading" aria-level="1">{_greeting()}, {name}</div>
                <div class="c360-subline">{subline}</div>
            </div>
            {header_actions_html(advisor)}
        </div>
        """
    )


# Benachrichtigungen und Benutzerbereich oben rechts; wird von Übersicht und Detailseite genutzt.
def header_actions_html(advisor: dict[str, str]) -> str:
    """Gibt die Beraterkennung im Kopfbereich zurück."""
    return (
        f'<div class="c360-header-actions">'
        f'<span class="c360-user"><span class="c360-user-avatar">{icon("user")}</span>'
        f'<span>{esc(advisor["first_name"])}<small>{t("advisor_role")}</small></span></span>'
        f"</div>"
    )
