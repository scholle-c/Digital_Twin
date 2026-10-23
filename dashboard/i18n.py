"""
Mehrsprachigkeit (Deutsch / Englisch).

- t(key):  feste Oberflächentexte (Buttons, Überschriften, Hinweise) aus UI_TEXT.
- tr(text): Texte aus den Mockdaten; Deutsch ist die Quelle, Englisch kommt aus
           data/translations_en.py. Fehlt eine Übersetzung, bleibt der deutsche Text.

Die aktive Sprache steht in st.session_state.lang und wird über den
Sprachumschalter in der Navigation gewechselt.
"""
from __future__ import annotations

import streamlit as st

from data.translations_en import DATA_EN

# Verfügbare Sprachen; die erste ist die Standardsprache.
LANGUAGES = ("de", "en")

# Alle festen Oberflächentexte. Platzhalter in {geschweiften Klammern} werden über t(..., name=wert) gefüllt.
UI_TEXT: dict[str, dict[str, str]] = {
    # Navigation und Kopfbereich
    "nav_aria": {"de": "Hauptnavigation", "en": "Main navigation"},
    "logo_sub": {"de": "Beratercockpit · Prototyp", "en": "Advisor cockpit · prototype"},
    "workspace_label": {"de": "Beratung / Kundenübersicht", "en": "Advisory / Customer overview"},
    "advisor_role": {"de": "Versicherungsberatung", "en": "Insurance advisor"},
    "nav_overview": {"de": "Übersicht", "en": "Overview"},
    "nav_customers": {"de": "Kunden", "en": "Customers"},
    "nav_tasks": {"de": "Aufgaben", "en": "Tasks"},

    # Reiter Digital Twin
    "detail_tabs": {"de": "Ansicht", "en": "View"},
    "tab_overview": {"de": "Übersicht", "en": "Overview"},
    "tab_twin": {"de": "Digital Twin", "en": "Digital twin"},
    "tab_regions": {"de": "Regionale Risiko-Heatmap", "en": "Regional risk heatmap"},
    "region_filter": {"de": "Bundesland", "en": "Federal state"},
    "region_all": {"de": "Deutschland gesamt", "en": "All of Germany"},
    "region_metric": {"de": "Kennzahl", "en": "Metric"},
    "region_step": {"de": "Monat relativ zu heute", "en": "Month relative to today"},
    "region_step_help": {"de": "Negativ = Vergangenheit (echte Vorfälle, 12-Monats-Fenster), positiv = Prognose aus den regionalen Trends.",
                         "en": "Negative = past (real incidents, 12-month window), positive = forecast from regional trends."},
    "region_past": {"de": "Vergangenheit", "en": "Past"},
    "region_now": {"de": "Heute", "en": "Today"},
    "region_future": {"de": "Prognose +{n} Monate", "en": "Forecast +{n} months"},
    "region_no_data": {"de": "Keine Vorfalldaten gefunden (generated_demodata/incidents.csv).", "en": "No incident data found (generated_demodata/incidents.csv)."},
    "region_map_note": {"de": "Dichte der Vorfälle, gewichtet nach Schwere. In der Prognose werden bekannte Orte mit dem regionalen Trend gewichtet. Rote Kreise: Naturereignisse aktiv oder erwartet.",
                        "en": "Incident density weighted by severity. In forecast mode, known locations are weighted by the regional trend. Red circles: active or expected natural events."},
    "region_kpi_note": {"de": "Erwartete Vorfälle pro Monat je Bundesland (Modellschätzung aus forecast.py) und Trend pro Jahr.",
                        "en": "Expected incidents per month per federal state (model estimate from forecast.py) and yearly trend."},
    "twin_heading": {"de": "Digital Twin im Vergleich zu {n} anderen Kunden", "en": "Digital twin compared with {n} other customers"},
    "twin_most_similar": {"de": "Ähnlichster Twin", "en": "Most similar twin"},
    "twin_damage": {"de": "Erwarteter Schaden (12 Monate)", "en": "Expected damage (12 months)"},
    "twin_damage_rank": {"de": "Rang {rank} von {n}", "en": "Rank {rank} of {n}"},
    "twin_outlier": {"de": "Auffälligste Kennzahl", "en": "Most notable metric"},
    "twin_outlier_value": {"de": "höher als {p} % der Kunden", "en": "higher than {p}% of customers"},
    "twin_position": {"de": "Position im Bestand", "en": "Position in the portfolio"},
    "twin_position_note": {
        "de": "Wahrscheinlichkeit innerhalb der nächsten 12 Monate. Modellschätzungen, keine bestätigten Ereignisse.",
        "en": "Probability within the next 12 months. Model estimates, not confirmed events.",
    },
    "twin_neighbors": {"de": "Ähnlichste Twins", "en": "Most similar twins"},
    "twin_median": {"de": "Median", "en": "Median"},
    "twin_average": {"de": "Ø alle Twins", "en": "Avg. all twins"},
    "twin_open": {"de": "{id} öffnen", "en": "Open {id}"},
    "lang_switch": {"de": "English", "en": "Deutsch"},
    "lang_switch_help": {"de": "Switch to English", "en": "Auf Deutsch umschalten"},
    "greeting_morning": {"de": "Guten Morgen", "en": "Good morning"},
    "greeting_day": {"de": "Guten Tag", "en": "Good afternoon"},
    "greeting_evening": {"de": "Guten Abend", "en": "Good evening"},
    "subline_one": {"de": "1 Kunde braucht diese Woche Ihre Aufmerksamkeit", "en": "1 customer needs your attention this week"},
    "subline_many": {"de": "{n} Kunden brauchen diese Woche Ihre Aufmerksamkeit", "en": "{n} customers need your attention this week"},
    "notifications": {"de": "Benachrichtigungen", "en": "Notifications"},

    # Kundenliste
    "prioritized_customers": {"de": "Priorisierte Kunden", "en": "Prioritized customers"},
    "rank": {"de": "Rang {n}", "en": "Rank {n}"},
    "open_customer": {"de": "{name} öffnen", "en": "Open {name}"},

    # Kundenübersicht
    "years": {"de": "{n}&nbsp;Jahre", "en": "{n}&nbsp;years"},
    "last_contact": {"de": "Letzter Kontakt: {date}", "en": "Last contact: {date}"},
    "why_see_this": {"de": "Warum sehe ich das?", "en": "Why am I seeing this?"},
    "why_title": {"de": "Diese Informationen haben zur Empfehlung geführt:", "en": "This information led to the recommendation:"},
    "why_note": {
        "de": "Die Empfehlung unterstützt Sie bei der Beratung. Sie ist keine automatische Entscheidung – Sie entscheiden gemeinsam mit dem Kunden.",
        "en": "The recommendation supports your advice. It is not an automated decision – you decide together with the customer.",
    },
    "most_important_now": {"de": "Das Wichtigste jetzt", "en": "Most important now"},
    "recommendation": {"de": "Empfehlung", "en": "Recommendation"},
    "customer_benefit": {"de": "Kundennutzen: {text}", "en": "Customer benefit: {text}"},
    "prepare_conversation": {"de": "Gespräch vorbereiten", "en": "Prepare conversation"},
    "close_preparation": {"de": "Vorbereitung schließen", "en": "Close preparation"},
    "guide_title": {"de": "Gesprächsvorbereitung für {name}", "en": "Conversation guide for {name}"},
    "guide_opening": {"de": "Empfohlener Gesprächseinstieg", "en": "Suggested opening"},
    "guide_questions": {"de": "Mögliche Fragen", "en": "Possible questions"},
    "guide_goal": {"de": "Ziel des Gesprächs:", "en": "Goal of the conversation:"},
    "quote": {"de": "„{text}“", "en": "“{text}”"},
    "current_coverage": {"de": "Aktuelle Absicherung", "en": "Current coverage"},
    "open_coverage": {"de": "Details zu {label} öffnen", "en": "Open details for {label}"},
    "new_events": {"de": "Neue Ereignisse", "en": "Recent events"},
    "new": {"de": "Neu", "en": "New"},
    "not_specified": {"de": "Keine Angaben", "en": "Not specified"},

    # Versicherungsdetailseite
    "breadcrumb_aria": {"de": "Pfad", "en": "Breadcrumb"},
    "back_to_overview": {"de": "Zurück zur Kundenübersicht", "en": "Back to customer overview"},
    "percent": {"de": "{n}&nbsp;%", "en": "{n}%"},
    "probability_aria": {"de": "Wahrscheinlichkeit {n} Prozent", "en": "Probability {n} percent"},
    "enrichment_title": {"de": "Content Enrichment", "en": "Content enrichment"},
    "enrichment_sub": {"de": "KI-gestützte Einschätzung aus freigegebenen Daten", "en": "AI-assisted assessment from approved data"},
    "no_signals": {"de": "Für diese Versicherung liegen keine auffälligen Signale vor.", "en": "There are no notable signals for this policy."},
    "more_signals_one": {"de": "1 weiteres Signal anzeigen", "en": "Show 1 more signal"},
    "more_signals_many": {"de": "{n} weitere Signale anzeigen", "en": "Show {n} more signals"},
    "probability_note": {
        "de": "Wahrscheinlichkeit = Modellschätzung, keine bestätigte Tatsache",
        "en": "Probability = model estimate, not a confirmed fact",
    },
    "why_assessment": {"de": "Warum diese Einschätzung?", "en": "Why this assessment?"},
    "reason_show": {"de": "{title}: Details anzeigen", "en": "{title}: show details"},
    "reason_hide": {"de": "{title}: Details schließen", "en": "{title}: hide details"},
    "sources_consent": {"de": "Datenquellen und Einwilligung ansehen", "en": "View data sources and consent"},
    "sources_used": {"de": "Verwendete Datenquellen", "en": "Data sources used"},
    "consent": {"de": "Einwilligung", "en": "Consent"},
    "open_info_one": {"de": "Offene Information", "en": "Open question"},
    "open_info_many": {"de": "Offene Informationen", "en": "Open questions"},
    "no_open_points": {"de": "Keine offenen Punkte.", "en": "No open points."},
    "clarify_in_conversation": {"de": "Im Gespräch klären", "en": "Clarify in conversation"},
    "noted": {"de": "Vorgemerkt", "en": "Noted"},
    "action_recommendation": {"de": "Handlungsempfehlung", "en": "Recommended action"},
    "how_title": {"de": "Wie entsteht die Empfehlung?", "en": "How is this recommendation made?"},
    "how_heading": {"de": "So entsteht die Empfehlung", "en": "How the recommendation is made"},
    "how_step1": {
        "de": "Freigegebene Daten (Vertrag, Adresse, öffentliche Quellen) werden zusammengeführt.",
        "en": "Approved data (contract, address, public sources) is combined.",
    },
    "how_step2": {
        "de": "Ein Modell schätzt, wie wahrscheinlich einzelne Ereignisse sind.",
        "en": "A model estimates how likely individual events are.",
    },
    "how_step3": {
        "de": "Regeln ordnen die Hinweise: Prävention vor Deckungslücke vor Cross-Selling.",
        "en": "Rules rank the signals: prevention before coverage gaps before cross-selling.",
    },
    "how_note": {
        "de": "Die Empfehlung unterstützt Sie. Die Entscheidung treffen Sie gemeinsam mit dem Kunden.",
        "en": "The recommendation supports you. You make the decision together with the customer.",
    },
    "remind_later": {"de": "Später erinnern", "en": "Remind me later"},
    "reminder_set": {"de": "Erinnerung gesetzt", "en": "Reminder set"},

    # Kurze Bestätigungen (Toasts)
    "toast_noted": {"de": "Frage für das Gespräch vorgemerkt", "en": "Question noted for the conversation"},
    "toast_reminder": {"de": "Erinnerung für morgen gesetzt", "en": "Reminder set for tomorrow"},
}


# Liefert die aktuell gewählte Sprache; vor der Initialisierung gilt Deutsch.
def current_language() -> str:
    """Gibt den Sprachcode der Sitzung zurück ("de" oder "en")."""
    return st.session_state.get("lang", LANGUAGES[0])


# Übersetzt einen festen Oberflächentext anhand seines Schlüssels und füllt Platzhalter.
def t(key: str, **values: object) -> str:
    """Gibt den Oberflächentext zum Schlüssel in der aktiven Sprache zurück."""
    text = UI_TEXT[key][current_language()]
    return text.format(**values) if values else text


# Übersetzt einen Text aus den Mockdaten; Deutsch wird unverändert zurückgegeben.
def tr(text: str) -> str:
    """Gibt die englische Fassung eines Datentextes zurück, falls Englisch aktiv ist."""
    if current_language() == "en":
        return DATA_EN.get(text, text)
    return text
