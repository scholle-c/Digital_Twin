"""
Sitzungszustand des Portals (st.session_state) und alle Zustandsänderungen.

Ansichten lesen den Zustand nur; Änderungen laufen über die Funktionen hier,
meist als Button-Callbacks. Eine spätere Backend-Anbindung ersetzt nur diese Datei.
"""
from __future__ import annotations

import copy
from datetime import datetime

import streamlit as st

from core.data import DEMO_LOGIN, initial_notifications, initial_policies, initial_profile

# Seiten des Portals: Schlüssel -> (Titel, Material-Icon).
PAGES = {
    "home": ("Übersicht", "home"),
    "profile": ("Mein Profil", "person"),
    "insurance": ("Meine Versicherungen", "verified_user"),
    "offers": ("Angebote", "local_offer"),
    "questionnaire": ("Umfragen", "assignment"),
    "trends": ("Trends & Analysen", "insights"),
    "notifications": ("Mitteilungen", "notifications"),
    "settings": ("Einstellungen", "settings"),
}


# Legt alle Zustandswerte beim ersten Aufruf an.
def init_state() -> None:
    """Initialisiert den Sitzungszustand mit Demodaten."""
    defaults = {
        "authenticated": False,
        "page": "home",
        "profile": initial_profile(),
        "policies": initial_policies(),
        "answers": {},
        "q_draft": {},
        "q_step": 0,
        "q_saved_at": None,
        "q_error": "",
        "q_submitted": False,
        "notifications": [],
        "dismissed_offers": [],
        "requested_offers": [],
        "open_offer": None,
        "open_policy": None,
        "edit_section": None,
        "consents": {"personalization": True, "regional_data": True, "marketing": False},
        "notify_channels": {"warnings": True, "contracts": True, "offers": False},
        "toast": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = copy.deepcopy(value)


# ------------------------------------------------------------
# Anmeldung (nur Demo, keine echte Authentifizierung)
# ------------------------------------------------------------

# Prüft die Demo-Zugangsdaten. Kundennummer oder E-Mail werden akzeptiert.
def check_login(identifier: str, password: str) -> bool:
    """Gibt True zurück, wenn die Eingaben dem Demo-Zugang entsprechen."""
    ident = identifier.strip().lower()
    return ident in (DEMO_LOGIN["customer_number"].lower(), DEMO_LOGIN["email"]) and password == DEMO_LOGIN["password"]


# Meldet den Demokunden an und lädt die Mitteilungen.
def login() -> None:
    """Setzt den Anmeldestatus und öffnet die Übersicht."""
    st.session_state.authenticated = True
    st.session_state.page = "home"
    if not st.session_state.notifications:
        st.session_state.notifications = initial_notifications(st.session_state.profile["postal_code"])


# Meldet ab; der Demo-Zustand (Profil, Antworten) bleibt für die nächste Anmeldung erhalten.
def logout() -> None:
    """Beendet die Demo-Sitzung."""
    st.session_state.authenticated = False


# Setzt alle Demodaten auf den Ausgangszustand zurück.
def reset_demo() -> None:
    """Löscht den Sitzungszustand vollständig."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]


# ------------------------------------------------------------
# Navigation und Rückmeldungen
# ------------------------------------------------------------

# Wechselt die Seite und schließt geöffnete Detailansichten.
def navigate(page: str) -> None:
    """Öffnet die angegebene Portalseite."""
    st.session_state.page = page
    st.session_state.open_offer = None
    st.session_state.open_policy = None
    st.session_state.edit_section = None
    st.session_state["search_query"] = ""


# Merkt eine kurze Bestätigung vor, die beim nächsten Rerun als Toast erscheint.
def notify(message: str) -> None:
    """Plant eine Toast-Meldung für den nächsten Seitenaufbau ein."""
    st.session_state.toast = message


# Anzahl ungelesener Mitteilungen für Badges.
def unread_count() -> int:
    """Gibt die Zahl ungelesener Mitteilungen zurück."""
    return sum(1 for n in st.session_state.notifications if not n["read"])


# Markiert eine Mitteilung als gelesen und öffnet optional die verknüpfte Seite.
def open_notification(note_id: str, go_to: bool = True) -> None:
    """Setzt eine Mitteilung auf gelesen und navigiert ggf. zur zugehörigen Seite."""
    for note in st.session_state.notifications:
        if note["id"] == note_id:
            note["read"] = True
            if go_to and note.get("page"):
                navigate(note["page"])


# Markiert alle Mitteilungen als gelesen.
def mark_all_read() -> None:
    """Setzt alle Mitteilungen auf gelesen."""
    for note in st.session_state.notifications:
        note["read"] = True


# ------------------------------------------------------------
# Angebote und Verträge
# ------------------------------------------------------------

# Klappt die Details eines Angebots auf bzw. zu.
def toggle_offer(product_id: str) -> None:
    """Öffnet oder schließt die Detailansicht eines Angebots."""
    st.session_state.open_offer = None if st.session_state.open_offer == product_id else product_id


# Blendet ein Angebot aus („Nicht relevant“).
def dismiss_offer(product_id: str) -> None:
    """Fügt das Angebot der Liste ausgeblendeter Angebote hinzu."""
    st.session_state.dismissed_offers.append(product_id)
    st.session_state.open_offer = None
    notify("Angebot ausgeblendet")


# Stellt alle ausgeblendeten Angebote wieder her.
def restore_offers() -> None:
    """Leert die Liste ausgeblendeter Angebote."""
    st.session_state.dismissed_offers = []


# Simuliert eine unverbindliche Anfrage und legt eine Mitteilung an.
def request_offer(product_id: str, product_name: str) -> None:
    """Markiert ein Angebot als angefragt und bestätigt dies per Mitteilung."""
    if product_id not in st.session_state.requested_offers:
        st.session_state.requested_offers.append(product_id)
        st.session_state.notifications.insert(0, {
            "id": f"req_{product_id}", "category": "offer", "date": datetime.now().date(),
            "title": f"Anfrage erhalten: {product_name}",
            "text": "Ihre Beraterin bzw. Ihr Berater meldet sich innerhalb von zwei Werktagen (Demo).",
            "page": "offers", "read": False,
        })
    notify("Anfrage gesendet (Demo)")


# Klappt die Detailansicht eines Vertrags auf bzw. zu.
def toggle_policy(policy_id: str) -> None:
    """Öffnet oder schließt die Detailansicht eines Vertrags."""
    st.session_state.open_policy = None if st.session_state.open_policy == policy_id else policy_id


# ------------------------------------------------------------
# Profil
# ------------------------------------------------------------

# Öffnet bzw. schließt den Bearbeitungsmodus eines Profilabschnitts.
def edit_section(section: str | None) -> None:
    """Setzt den Profilabschnitt, der gerade bearbeitet wird."""
    st.session_state.edit_section = section
    st.session_state.pf_errors = []


# Übernimmt geänderte Profilfelder und hält Fragebogenangaben konsistent.
def save_profile(changes: dict) -> None:
    """Speichert Profiländerungen und schließt den Bearbeitungsmodus."""
    st.session_state.profile.update(changes)
    if "children" in changes and st.session_state.answers:
        st.session_state.answers["children"] = changes["children"]
    st.session_state.edit_section = None
    notify("Profil gespeichert")


# ------------------------------------------------------------
# Fragebogen
# ------------------------------------------------------------

# Speichert den Zwischenstand mit Uhrzeit.
def save_draft(values: dict) -> None:
    """Übernimmt Werte in den Entwurf und merkt sich die Speicherzeit."""
    st.session_state.q_draft.update(values)
    st.session_state.q_saved_at = datetime.now().strftime("%H:%M")


# Übernimmt den Entwurf als gültige Antworten; Dashboard und Angebote nutzen sie ab sofort.
def submit_questionnaire() -> None:
    """Schließt den Fragebogen ab und personalisiert das Portal."""
    st.session_state.answers = copy.deepcopy(st.session_state.q_draft)
    st.session_state.q_submitted = True
    if "children" in st.session_state.answers:
        st.session_state.profile["children"] = st.session_state.answers["children"]
    for note in st.session_state.notifications:
        if note["id"] == "questionnaire":
            note["read"] = True
    notify("Danke! Ihre Empfehlungen wurden aktualisiert.")


# Öffnet einen abgeschlossenen Fragebogen erneut zum Bearbeiten.
def reopen_questionnaire(step: int = 0) -> None:
    """Setzt den Fragebogen in den Bearbeitungsmodus auf den angegebenen Schritt."""
    st.session_state.q_draft = copy.deepcopy(st.session_state.answers) or st.session_state.q_draft
    st.session_state.q_submitted = False
    st.session_state.q_step = step
