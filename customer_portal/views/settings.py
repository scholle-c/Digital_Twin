"""
Einstellungen: Einwilligungen zur Datennutzung, Benachrichtigungen, Sicherheit und Demo-Verwaltung.
"""
from __future__ import annotations

import streamlit as st

from core.state import logout, notify, reset_demo
from ui.components import badge, icon, page_header, render_html


# Übernimmt einen Schalter in den Zustand (Callback der Toggles).
def _store(group: str, key: str) -> None:
    """Speichert den Wert eines Einstellungsschalters."""
    st.session_state[group][key] = st.session_state[f"set_{group}_{key}"]
    notify("Einstellung gespeichert")


# Baut die Einstellungsseite auf.
def render(ctx: dict) -> None:
    """Rendert Datenschutz-, Benachrichtigungs- und Sicherheitseinstellungen."""
    page_header("Einstellungen", "Datenschutz, Benachrichtigungen und Konto.", "settings")
    left, right = st.columns(2, gap="medium")
    with left, st.container(key="set_privacy"):
        render_html(f'<div class="dt-card-head"><h3 class="dt-h3">Datenschutz & Einwilligungen</h3>{badge("DSGVO", "info", "lock")}</div>')
        consents = st.session_state.consents
        for key, label, hint in [
            ("personalization", "Personalisierte Empfehlungen", "Digital Twin nutzt Profil, Verträge und Fragebogen."),
            ("regional_data", "Regionale Risikodaten", "Wetter- und Schadendaten für Ihre Region einbeziehen."),
            ("marketing", "Werbliche Ansprache", "Angebote per E-Mail oder Telefon erhalten."),
        ]:
            st.toggle(label, value=consents[key], key=f"set_consents_{key}", help=hint,
                      on_change=_store, args=("consents", key))
        if not consents["personalization"]:
            render_html(f'<div class="dt-callout dt-callout-warn">{icon("info", "ms-sm")}<span>Ohne Einwilligung zeigen wir '
                        f"nur allgemeine Informationen statt persönlicher Empfehlungen.</span></div>")
        render_html('<p class="dt-tiny">Sie können Einwilligungen jederzeit widerrufen. Gesundheitsdaten werden '
                    "ohne ausdrückliche Einwilligung nie für Empfehlungen genutzt.</p>")
    with right:
        with st.container(key="set_notify"):
            render_html('<h3 class="dt-h3">Benachrichtigungen</h3>')
            channels = st.session_state.notify_channels
            for key, label in [("warnings", "Unwetter- und Sicherheitswarnungen"), ("contracts", "Vertrags- und Beitragsinfos"),
                               ("offers", "Neue Empfehlungen")]:
                st.toggle(label, value=channels[key], key=f"set_notify_channels_{key}", on_change=_store,
                          args=("notify_channels", key))
        with st.container(key="set_account"):
            render_html('<h3 class="dt-h3">Konto & Sicherheit</h3>'
                        f'<div class="dt-callout">{icon("fingerprint", "ms-sm")}<span>Zwei-Faktor-Anmeldung und biometrischer '
                        f"Login sind im Prototyp als Konzept dargestellt.</span></div>")
            c1, c2 = st.columns(2)
            c1.button("Abmelden", key="set_logout", icon=":material/logout:", on_click=logout)
            c2.button("Demo zurücksetzen", key="set_reset", icon=":material/restart_alt:", on_click=reset_demo,
                      help="Setzt Profil, Fragebogen, Angebote und Mitteilungen auf den Ausgangszustand zurück.")
