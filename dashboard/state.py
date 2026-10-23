"""
Zustandsverwaltung über st.session_state.

Alle Klicks (Kundenkarte, Versicherungskarte, Gesprächsvorbereitung, Vormerken,
Erinnern) ändern den Zustand ausschließlich über diese Callbacks. Die Darstellung
liest den Zustand nur aus und bleibt dadurch frei von Seiteneffekten.
"""
from __future__ import annotations

import streamlit as st

# Mögliche Ansichten im Hauptbereich.
VIEW_OVERVIEW = "overview"
VIEW_COVERAGE = "coverage"


# Legt beim ersten Aufruf die Standardwerte an. Bei späteren Reruns bleiben
# die vorhandenen Werte erhalten, damit Auswahl und Vormerkungen stabil bleiben.
def init_session_state(default_customer_id: str) -> None:
    """Initialisiert Sprache, Ansicht, Auswahl, Gesprächsvorbereitung und Vormerkungen."""
    st.session_state.setdefault("lang", "de")
    st.session_state.setdefault("view", VIEW_OVERVIEW)
    st.session_state.setdefault("selected_customer_id", default_customer_id)
    st.session_state.setdefault("selected_coverage", None)
    st.session_state.setdefault("guide_open", False)
    st.session_state.setdefault("open_reason", None)
    st.session_state.setdefault("noted_questions", [])
    st.session_state.setdefault("reminders", [])
    st.session_state.setdefault("pending_toast", None)


# Schließt alle Bereiche, die nur zu einer bestimmten Ansicht gehören.
def _reset_view_details() -> None:
    """Setzt Gesprächsvorbereitung und aufgeklappte Begründung zurück."""
    st.session_state.guide_open = False
    st.session_state.open_reason = None


# Wird beim Klick auf eine Kundenkarte ausgelöst und führt immer zur Übersicht.
def select_customer(customer_id: str) -> None:
    """Wählt einen Kunden aus und zeigt dessen Übersicht an."""
    if st.session_state.selected_customer_id != customer_id:
        st.session_state.selected_customer_id = customer_id
        _reset_view_details()
    st.session_state.selected_coverage = None
    st.session_state.view = VIEW_OVERVIEW


# Öffnet die Versicherungsdetailseite des ausgewählten Kunden.
def open_coverage(coverage_key: str) -> None:
    """Wechselt zur Detailseite der angeklickten Versicherung."""
    st.session_state.selected_coverage = coverage_key
    st.session_state.view = VIEW_COVERAGE
    _reset_view_details()


# Zurück aus der Versicherungsdetailseite zur Kundenübersicht.
def back_to_overview() -> None:
    """Wechselt von der Versicherungsdetailseite zurück zur Kundenübersicht."""
    st.session_state.view = VIEW_OVERVIEW
    st.session_state.selected_coverage = None
    _reset_view_details()


# Öffnet bzw. schließt die Gesprächsvorbereitung zum ausgewählten Kunden.
def toggle_guide() -> None:
    """Schaltet die Gesprächsvorbereitung ein oder aus."""
    st.session_state.guide_open = not st.session_state.guide_open


# Klappt die Erläuterung einer Begründung („Warum diese Einschätzung?“) auf oder zu.
def toggle_reason(reason_id: str) -> None:
    """Zeigt die Details einer Begründung an oder blendet sie wieder aus."""
    current = st.session_state.open_reason
    st.session_state.open_reason = None if current == reason_id else reason_id


# Merkt eine offene Frage für das nächste Kundengespräch vor.
def note_question(question_id: str) -> None:
    """Fügt eine offene Information der Liste der vorgemerkten Gesprächsfragen hinzu."""
    if question_id not in st.session_state.noted_questions:
        st.session_state.noted_questions.append(question_id)
    st.session_state.pending_toast = "toast_noted"


# Setzt eine Erinnerung für die Handlungsempfehlung (im Prototyp nur in der Sitzung).
def set_reminder(reminder_id: str) -> None:
    """Speichert eine Erinnerung und kündigt eine kurze Bestätigung an."""
    if reminder_id not in st.session_state.reminders:
        st.session_state.reminders.append(reminder_id)
    st.session_state.pending_toast = "toast_reminder"


# Wechselt die Oberflächensprache zwischen Deutsch und Englisch; Auswahl und Ansicht bleiben erhalten.
def toggle_language() -> None:
    """Schaltet st.session_state.lang zwischen "de" und "en" um."""
    st.session_state.lang = "en" if st.session_state.lang == "de" else "de"
