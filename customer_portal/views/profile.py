"""
Mein Profil: persönliche Daten (geschützt), Haushalt & Lebenssituation sowie Präferenzen.

Jeder Abschnitt hat einen Anzeige- und einen Bearbeitungsmodus mit Validierung.
Änderungen an Familie oder Beruf wirken sich direkt auf Dashboard und Angebote aus.
"""
from __future__ import annotations

import re
from datetime import date

import streamlit as st

from core.data import EVENT_LABELS, FEDERAL_STATES, INTERESTS, OCCUPATIONS, RELATIONSHIP, TODAY, life_events_of
from core.state import edit_section, navigate, report_life_event, save_profile
from ui.components import badge, esc, icon, page_header, render_html

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE = re.compile(r"^\+?[\d\s/()-]{7,20}$")
INTEREST_OPTIONS = list(INTERESTS.values())
CHANNELS = ["E-Mail", "App-Benachrichtigung", "Telefon", "Post"]


# Baut die Profilseite auf.
def render(ctx: dict) -> None:
    """Rendert Kopf, Profilkarte und die drei Abschnitte."""
    profile = ctx["profile"]
    page_header("Mein Profil", "Ihre Angaben bilden die Grundlage für Ihren Digital Twin.", "person")
    initials = f"{profile['first_name'][:1]}{profile['last_name'][:1]}"
    render_html(
        f'<div class="dt-profile-hero"><span class="dt-avatar">{esc(initials)}</span><div>'
        f'<div class="dt-profile-name">{esc(profile["first_name"])} {esc(profile["last_name"])}</div>'
        f'<div class="dt-muted">Kunden-ID {esc(profile["customer_id"])} · Kunde seit {profile["customer_since"].year}</div></div>'
        f'{badge("Identität bestätigt", "ok", "verified")}</div>'
    )
    left, right = st.columns([1.15, 1], gap="medium")
    with left:
        _personal(profile)
    with right:
        _household(profile)
        _life_events(profile)
        _preferences(profile)


# Kopf eines Abschnitts mit Bearbeiten-Button.
def _section_head(key: str, title: str, sub: str, protected: bool = False) -> bool:
    """Rendert den Abschnittskopf; gibt True zurück, wenn der Abschnitt bearbeitet wird."""
    editing = st.session_state.edit_section == key
    lock = badge("Geschützte Daten", "info", "lock") if protected else ""
    render_html(f'<div class="dt-card-head"><div><h3 class="dt-h3">{esc(title)}</h3><small class="dt-muted">{esc(sub)}</small></div>{lock}</div>')
    if not editing:
        st.button("Bearbeiten", key=f"edit_{key}", icon=":material/edit:", on_click=edit_section, args=(key,))
    return editing


# Anzeige von Feldern als Definitionsliste.
def _fields(rows: list[tuple[str, str]]) -> None:
    """Zeigt Beschriftung-Wert-Paare an."""
    items = "".join(f"<div><dt>{esc(label)}</dt><dd>{esc(value) or '–'}</dd></div>" for label, value in rows)
    render_html(f'<dl class="dt-dl">{items}</dl>')


# Formular-Fußzeile: Speichern prüft die Eingaben im Callback, Fehler erscheinen im Formular.
def _form_buttons(handler) -> None:
    """Rendert Speichern/Abbrechen und zeigt Validierungsfehler des letzten Speicherversuchs."""
    for error in st.session_state.get("pf_errors", []):
        st.error(error)
    save_col, cancel_col = st.columns(2)
    with save_col:
        st.form_submit_button("Speichern", type="primary", icon=":material/check:", on_click=_submit, args=(handler,))
    with cancel_col:
        st.form_submit_button("Abbrechen", on_click=edit_section, args=(None,))


# Callback: übernimmt die Änderungen nur, wenn die Prüfung keine Fehler meldet.
def _submit(handler) -> None:
    """Validiert die Formularwerte und speichert sie bei Erfolg."""
    changes, errors = handler(st.session_state)
    st.session_state.pf_errors = errors
    if not errors:
        save_profile(changes)


# Prüft und sammelt die persönlichen Daten aus den Formularfeldern.
def _personal_changes(s) -> tuple[dict, list[str]]:
    """Gibt Änderungen und Fehlermeldungen für den Abschnitt „Persönliche Daten“ zurück."""
    first, last, street, postal = s.pf_first.strip(), s.pf_last.strip(), s.pf_street.strip(), s.pf_postal.strip()
    city, email, phone, birth = s.pf_city.strip(), s.pf_email.strip(), s.pf_phone.strip(), s.pf_birth
    errors = []
    if not first or not last:
        errors.append("Vor- und Nachname sind Pflichtfelder.")
    if not street or not city:
        errors.append("Bitte eine vollständige Adresse angeben.")
    if not re.fullmatch(r"\d{5}", postal):
        errors.append("Die Postleitzahl besteht aus 5 Ziffern.")
    if not EMAIL.match(email):
        errors.append("Bitte eine gültige E-Mail-Adresse eingeben.")
    if phone and not PHONE.match(phone):
        errors.append("Die Telefonnummer enthält ungültige Zeichen.")
    if birth is None or (TODAY - birth).days < 18 * 365:
        errors.append("Für das Kundenportal müssen Sie volljährig sein.")
    return {"first_name": first, "last_name": last, "birth_date": birth, "street": street, "postal_code": postal,
            "city": city, "email": email, "phone": phone}, errors


# Prüft und sammelt Haushalt und Lebenssituation.
def _household_changes(s) -> tuple[dict, list[str]]:
    """Gibt Änderungen und Fehlermeldungen für den Abschnitt „Haushalt“ zurück."""
    errors = []
    if s.pf_household < s.pf_children + 1:
        errors.append("Im Haushalt müssen mindestens so viele Personen leben wie Kinder plus Sie selbst.")
    return {"relationship_status": s.pf_rel, "children": int(s.pf_children), "household_size": int(s.pf_household),
            "occupation": s.pf_occupation, "interests": s.pf_interests}, errors


# Prüft und sammelt die Kommunikationspräferenzen.
def _prefs_changes(s) -> tuple[dict, list[str]]:
    """Gibt Änderungen und Fehlermeldungen für den Abschnitt „Präferenzen“ zurück."""
    errors = [] if s.pf_channels else ["Bitte mindestens einen Kontaktweg wählen."]
    return {"channels": s.pf_channels, "contact_time": s.pf_time, "newsletter": s.pf_newsletter}, errors


# Abschnitt „Persönliche Daten“ (sensibel).
def _personal(profile: dict) -> None:
    """Zeigt bzw. bearbeitet Name, Geburtsdatum, Adresse und Kontaktdaten."""
    with st.container(key="sec_personal"):
        if not _section_head("personal", "Persönliche Daten", "Name, Adresse und Kontakt", protected=True):
            _fields([
                ("Name", f"{profile['first_name']} {profile['last_name']}"),
                ("Geburtsdatum", f"{profile['birth_date']:%d.%m.%Y}"),
                ("Adresse", f"{profile['street']}, {profile['postal_code']} {profile['city']}"),
                ("E-Mail", profile["email"]),
                ("Telefon", profile["phone"]),
            ])
            render_html(
                f'<div class="dt-callout">{icon("shield_lock", "ms-sm")}<span>Ihre persönlichen Daten werden verschlüsselt '
                f"übertragen und nur für Ihren Vertrag genutzt (Konzept). Für Empfehlungen gelten Ihre Einwilligungen.</span></div>"
            )
            return
        with st.form("form_personal"):
            c1, c2 = st.columns(2)
            c1.text_input("Vorname *", profile["first_name"], key="pf_first")
            c2.text_input("Nachname *", profile["last_name"], key="pf_last")
            st.date_input("Geburtsdatum *", profile["birth_date"], min_value=date(1920, 1, 1),
                          max_value=TODAY, format="DD.MM.YYYY", key="pf_birth")
            st.text_input("Straße und Hausnummer *", profile["street"], key="pf_street")
            c3, c4 = st.columns([1, 2])
            c3.text_input("PLZ *", profile["postal_code"], key="pf_postal")
            c4.text_input("Ort *", profile["city"], key="pf_city")
            st.text_input("E-Mail *", profile["email"], key="pf_email")
            st.text_input("Telefon", profile["phone"], key="pf_phone")
            _form_buttons(_personal_changes)


# Abschnitt „Haushalt & Lebenssituation“ – beeinflusst direkt die Empfehlungen.
def _household(profile: dict) -> None:
    """Zeigt bzw. bearbeitet Familienstand, Kinder, Haushalt, Beruf und Interessen."""
    with st.container(key="sec_household"):
        if not _section_head("household", "Haushalt & Lebenssituation", "Grundlage für passende Empfehlungen"):
            _fields([
                ("Familienstand", profile["relationship_status"]),
                ("Kinder im Haushalt", str(profile["children"])),
                ("Personen im Haushalt", str(profile["household_size"])),
                ("Beruf", profile["occupation"]),
                ("Interessen", ", ".join(profile["interests"])),
            ])
            return
        with st.form("form_household"):
            relationships = list(RELATIONSHIP.values())
            occupations = list(OCCUPATIONS.values())
            st.selectbox("Familienstand", relationships, relationships.index(profile["relationship_status"]), key="pf_rel")
            c1, c2 = st.columns(2)
            c1.number_input("Kinder im Haushalt", 0, 10, int(profile["children"]), key="pf_children")
            c2.number_input("Personen im Haushalt", 1, 12, int(profile["household_size"]), key="pf_household")
            st.selectbox("Beruf", occupations, occupations.index(profile["occupation"]), key="pf_occupation")
            st.multiselect("Interessen", sorted(set(INTEREST_OPTIONS) | set(profile["interests"])),
                           profile["interests"], key="pf_interests")
            _form_buttons(_household_changes)


# Abschnitt „Lebensereignisse“: gemeldete Ereignisse und Formular für ein neues (z. B. Umzug).
def _life_events(profile: dict) -> None:
    """Zeigt die gemeldeten Lebensereignisse und erlaubt, ein neues zu melden."""
    with st.container(key="sec_events"):
        render_html('<div class="dt-card-head"><div><h3 class="dt-h3">Lebensereignisse</h3>'
                    '<small class="dt-muted">Was sich bei Ihnen verändert hat – Ihr Digital Twin passt die Empfehlungen an</small></div></div>')
        events = life_events_of(profile["customer_id"])
        _fields([(e["date"].strftime("%d.%m.%Y"), e["label"]) for e in events[:5]] or [("Bisher", "keine Ereignisse gemeldet")])
        if not st.session_state.get("event_form_open"):
            st.button("Ereignis melden", key="event_open", icon=":material/add_circle:",
                      on_click=lambda: st.session_state.update(event_form_open=True))
            return
        event_type = st.selectbox("Was ist passiert?", list(EVENT_LABELS), format_func=lambda k: EVENT_LABELS[k], key="ev_type")
        with st.form("form_event"):
            event_date = st.date_input("Wann?", TODAY, max_value=TODAY, format="DD.MM.YYYY", key="ev_date")
            new_postal = new_city = new_state = ""
            if event_type == "umzug":
                c1, c2 = st.columns([1, 2])
                new_postal = c1.text_input("Neue PLZ *", key="ev_postal")
                new_city = c2.text_input("Neuer Ort *", key="ev_city")
                states = FEDERAL_STATES
                current = profile.get("federal_state", "Bayern")
                new_state = st.selectbox("Bundesland", states, states.index(current) if current in states else 1, key="ev_state")
            save_col, cancel_col = st.columns(2)
            submitted = save_col.form_submit_button("Speichern", type="primary", icon=":material/check:")
            cancel_col.form_submit_button("Abbrechen", on_click=lambda: st.session_state.update(event_form_open=False))
        if submitted:
            if event_type == "umzug" and (not re.fullmatch(r"\d{5}", new_postal.strip()) or not new_city.strip()):
                st.error("Für einen Umzug bitte neue PLZ (5 Ziffern) und Ort angeben.")
            else:
                report_life_event(event_type, event_date, new_postal.strip(), new_city.strip(), new_state)
                st.rerun()


# Abschnitt „Präferenzen & Kommunikation“.
def _preferences(profile: dict) -> None:
    """Zeigt bzw. bearbeitet Kontaktwege, Erreichbarkeit und Newsletter."""
    with st.container(key="sec_prefs"):
        if not _section_head("prefs", "Präferenzen & Kommunikation", "Wie wir Sie erreichen dürfen"):
            _fields([
                ("Kontaktwege", ", ".join(profile["channels"])),
                ("Beste Erreichbarkeit", profile["contact_time"]),
                ("Newsletter", "Ja" if profile["newsletter"] else "Nein"),
            ])
            st.button("Einwilligungen verwalten", key="to_settings", icon=":material/tune:", on_click=navigate, args=("settings",))
            return
        with st.form("form_prefs"):
            st.multiselect("Kontaktwege", CHANNELS, profile["channels"], key="pf_channels")
            times = ["Morgens", "Mittags", "Abends", "Egal"]
            st.radio("Beste Erreichbarkeit", times, times.index(profile["contact_time"]), horizontal=True, key="pf_time")
            st.toggle("Newsletter mit Tipps zu Prävention erhalten", profile["newsletter"], key="pf_newsletter")
            _form_buttons(_prefs_changes)
