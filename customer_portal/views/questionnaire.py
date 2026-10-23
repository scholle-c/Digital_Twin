"""
Umfragen: mehrstufiger Fragebogen zur Lebenssituation mit Fortschrittsanzeige,
bedingten Fragen, Zwischenspeichern, Prüfseite und Absenden.

Die Fragen sind als Daten definiert (STEPS). Neue Fragen brauchen nur einen Eintrag;
Darstellung, Validierung und Zusammenfassung funktionieren automatisch.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import streamlit as st

from core.state import navigate, reopen_questionnaire, save_draft, submit_questionnaire
from ui.components import esc, icon, page_header, render_html


# Eine Frage: Feldname, Beschriftung, Typ (radio, checkbox, select, number, text) und optionale Bedingung.
@dataclass
class Question:
    """Definition einer Frage im Fragebogen."""

    field: str
    label: str
    kind: str
    options: list = field(default_factory=list)
    required: bool = True
    help: str = ""
    min_value: int = 0
    max_value: int = 1000
    condition: Callable[[Callable[[str], object]], bool] | None = None


# Ein Schritt mit Titel, Erklärung und zugehörigen Fragen.
@dataclass
class Step:
    """Ein Schritt des Fragebogens."""

    title: str
    intro: str
    icon: str
    questions: list[Question]


YES_NO = ["Ja", "Nein"]
STEPS = [
    Step("Wohnen", "Wie wohnen Sie aktuell?", "home", [
        Question("housing_type", "Wie ist Ihre aktuelle Wohnsituation?", "radio",
                 ["Wohnung", "Reihen-/Doppelhaus", "Freistehendes Haus", "WG / Sonstiges"]),
        Question("ownership", "Wohnen Sie zur Miete oder im Eigentum?", "radio", ["Miete", "Eigentum"]),
        Question("building_year", "Baujahr des Gebäudes (ungefähr)", "number", required=False,
                 min_value=1800, max_value=2026, condition=lambda v: v("ownership") == "Eigentum"),
        Question("living_space", "Wohnfläche in m²", "number", min_value=10, max_value=1000,
                 help="Hilft, die passende Versicherungssumme für Ihren Hausrat zu schätzen."),
        Question("basement", "Gibt es einen Keller?", "radio", YES_NO),
        Question("smoke_detector", "Sind Rauchmelder installiert?", "radio", ["Ja, in allen Räumen", "Teilweise", "Nein"],
                 help="Wird direkt an Ihren Digital Twin übergeben und verändert die Brandrisiko-Einschätzung."),
    ]),
    Step("Familie", "Hat sich in Ihrem Leben etwas verändert?", "family_restroom", [
        Question("family_changed", "Hat sich Ihre Familiensituation in den letzten 12 Monaten verändert?", "radio", YES_NO),
        Question("family_change_types", "Was hat sich verändert?", "checkbox",
                 ["Heirat / Partnerschaft", "Geburt / Adoption", "Trennung", "Kind ausgezogen", "Pflegefall in der Familie"],
                 condition=lambda v: v("family_changed") == "Ja"),
        Question("children", "Wie viele Kinder leben in Ihrem Haushalt?", "number", min_value=0, max_value=10),
    ]),
    Step("Mobilität", "Wie sind Sie unterwegs?", "directions_car", [
        Question("owns_car", "Besitzen Sie ein Auto?", "radio", YES_NO),
        Question("car_type", "Welcher Antrieb?", "select", ["Verbrenner", "Hybrid", "Elektro"],
                 condition=lambda v: v("owns_car") == "Ja"),
        Question("car_count", "Wie viele Fahrzeuge?", "select", ["1", "2", "3 oder mehr"],
                 condition=lambda v: v("owns_car") == "Ja"),
        Question("bikes", "Welche Räder nutzen Sie?", "checkbox", ["Fahrrad", "E-Bike", "Lastenrad", "Keines"], required=False),
        Question("commute", "Wie kommen Sie meistens zur Arbeit?", "select",
                 ["Auto", "Öffentliche Verkehrsmittel", "Fahrrad", "Zu Fuß", "Homeoffice"]),
    ]),
    Step("Prioritäten", "Was ist Ihnen besonders wichtig?", "star", [
        Question("priorities", "Welche Themen sind Ihnen am wichtigsten?", "checkbox",
                 ["Finanzielle Sicherheit", "Gesundheit", "Familienschutz", "Reisen", "Nachhaltigkeit"],
                 help="Mehrfachauswahl möglich."),
        Question("travel_frequency", "Wie oft reisen Sie ins Ausland?", "select", ["Selten", "1× pro Jahr", "2–3× pro Jahr", "Häufiger"],
                 condition=lambda v: "Reisen" in (v("priorities") or [])),
        Question("health_focus", "Welche Gesundheitsleistungen interessieren Sie?", "checkbox",
                 ["Zahn", "Brille / Sehhilfe", "Heilpraktiker", "Einbettzimmer im Krankenhaus"], required=False,
                 condition=lambda v: "Gesundheit" in (v("priorities") or [])),
    ]),
]


# Liest den aktuellen Wert einer Frage: erst das Widget, sonst den gespeicherten Entwurf.
def _value(name: str) -> object:
    """Gibt den aktuellen Wert eines Fragebogenfelds zurück."""
    question = next((q for s in STEPS for q in s.questions if q.field == name), None)
    if question and question.kind == "checkbox":
        keys = [f"q_{name}__{i}" for i in range(len(question.options))]
        if any(k in st.session_state for k in keys):
            return [opt for opt, k in zip(question.options, keys) if st.session_state.get(k)]
    elif f"q_{name}" in st.session_state:
        return st.session_state[f"q_{name}"]
    return st.session_state.q_draft.get(name)


# Sichtbare Fragen eines Schritts (bedingte Fragen nur, wenn ihre Bedingung erfüllt ist).
def _visible(step: Step) -> list[Question]:
    """Gibt die Fragen zurück, die im aktuellen Zustand angezeigt werden."""
    return [q for q in step.questions if q.condition is None or q.condition(_value)]


# Sammelt die Werte des aktuellen Schritts und prüft Pflichtfelder.
def _collect(step: Step) -> tuple[dict, list[str]]:
    """Gibt die Werte des Schritts und fehlende Pflichtfelder zurück."""
    values, missing = {}, []
    for q in _visible(step):
        value = _value(q.field)
        values[q.field] = value
        if q.required and (value is None or value == [] or value == ""):
            missing.append(q.label)
    # Antworten auf ausgeblendete Folgefragen entfernen, damit keine veralteten Angaben bleiben.
    for q in step.questions:
        if q not in _visible(step):
            values[q.field] = None
    return values, missing


# Callback „Weiter“: speichert und geht nur bei vollständigen Pflichtfeldern weiter.
def _next() -> None:
    """Prüft den aktuellen Schritt und wechselt zum nächsten."""
    values, missing = _collect(STEPS[st.session_state.q_step])
    save_draft({k: v for k, v in values.items()})
    if missing:
        st.session_state.q_error = "Bitte beantworten Sie: " + "; ".join(missing)
        return
    st.session_state.q_error = ""
    st.session_state.q_step += 1


# Callback „Zurück“: speichert ohne Prüfung und geht einen Schritt zurück.
def _back() -> None:
    """Speichert den Schritt und geht zurück."""
    if st.session_state.q_step < len(STEPS):
        save_draft(_collect(STEPS[st.session_state.q_step])[0])
    st.session_state.q_error = ""
    st.session_state.q_step = max(0, st.session_state.q_step - 1)


# Callback „Zwischenspeichern“.
def _save() -> None:
    """Speichert den aktuellen Schritt als Entwurf (auf der Prüfseite nur die Uhrzeit)."""
    step = st.session_state.q_step
    save_draft(_collect(STEPS[step])[0] if step < len(STEPS) else {})
    st.session_state.q_error = ""


# Callback auf der Prüfseite: Schritt gezielt bearbeiten.
def _goto(step: int) -> None:
    """Springt zu einem Schritt des Fragebogens."""
    st.session_state.q_step = step


# Baut den Fragebogen bzw. die Abschlussansicht auf.
def render(ctx: dict) -> None:
    """Rendert den Fragebogen."""
    page_header("Umfragen", "Ihre Lebenssituation in 4 kurzen Schritten – für Empfehlungen, die wirklich passen.", "assignment")
    if st.session_state.q_submitted:
        _done()
        return
    # Bekannte Angaben aus dem Profil vorbelegen, damit nichts doppelt eingegeben werden muss.
    st.session_state.q_draft.setdefault("children", ctx["profile"]["children"])
    step_index = st.session_state.q_step
    _progress(step_index)
    with st.container(key="q_card"):
        if step_index < len(STEPS):
            _render_step(STEPS[step_index])
        else:
            _review()


# Fortschrittsanzeige mit Schrittnamen.
def _progress(step_index: int) -> None:
    """Zeigt Fortschrittsbalken und Schrittliste."""
    total = len(STEPS) + 1
    names = [s.title for s in STEPS] + ["Prüfen"]
    chips = "".join(
        f'<li class="{"is-done" if i < step_index else "is-current" if i == step_index else ""}">'
        f'<span>{"✓" if i < step_index else i + 1}</span>{esc(n)}</li>'
        for i, n in enumerate(names)
    )
    pct = round(100 * step_index / (total - 1))
    render_html(
        f'<div class="dt-progress" role="progressbar" aria-valuenow="{pct}" aria-valuemin="0" aria-valuemax="100">'
        f'<div class="dt-progress-bar"><span style="width:{pct}%"></span></div><ol class="dt-steps">{chips}</ol></div>'
    )


# Ein Fragebogenschritt mit allen sichtbaren Fragen und Navigation.
def _render_step(step: Step) -> None:
    """Rendert die Fragen eines Schritts."""
    render_html(f'<div class="dt-q-head">{icon(step.icon, "ms-lg")}<div><h2 class="dt-h2">{esc(step.title)}</h2>'
                f'<p class="dt-muted">{esc(step.intro)}</p></div></div>')
    draft = st.session_state.q_draft
    for q in _visible(step):
        key = f"q_{q.field}"
        saved = draft.get(q.field)
        if q.kind == "radio":
            index = q.options.index(saved) if saved in q.options else None
            st.radio(q.label, q.options, index=index, key=key, help=q.help or None, horizontal=len(q.options) <= 3)
        elif q.kind == "select":
            index = q.options.index(saved) if saved in q.options else None
            st.selectbox(q.label, q.options, index=index, key=key, help=q.help or None, placeholder="Bitte wählen …")
        elif q.kind == "number":
            st.number_input(q.label, min_value=q.min_value, max_value=q.max_value, step=1,
                            value=int(saved) if saved is not None else None, key=key, help=q.help or None,
                            placeholder="Zahl eingeben")
        elif q.kind == "checkbox":
            render_html(f'<p class="dt-q-label">{esc(q.label)}{" *" if q.required else ""}</p>')
            if q.help:
                render_html(f'<p class="dt-tiny">{esc(q.help)}</p>')
            selected = saved or []
            columns = st.columns(2)
            for i, option in enumerate(q.options):
                columns[i % 2].checkbox(option, value=option in selected, key=f"{key}__{i}")
    if st.session_state.q_error:
        st.error(st.session_state.q_error)
    _nav_buttons(first=st.session_state.q_step == 0)


# Zurück / Zwischenspeichern / Weiter.
def _nav_buttons(first: bool, last: bool = False) -> None:
    """Rendert die Navigationsbuttons des Fragebogens."""
    back_col, save_col, next_col = st.columns([1, 1.3, 1])
    with back_col:
        st.button("Zurück", key="q_back", icon=":material/arrow_back:", on_click=_back, disabled=first)
    with save_col:
        st.button("Zwischenspeichern", key="q_save", icon=":material/save:", on_click=_save)
        if st.session_state.q_saved_at:
            render_html(f'<p class="dt-tiny">Gespeichert um {st.session_state.q_saved_at} Uhr</p>')
    with next_col:
        if last:
            st.button("Absenden", key="q_submit", type="primary", icon=":material/send:", on_click=submit_questionnaire)
        else:
            st.button("Weiter", key="q_next", type="primary", icon=":material/arrow_forward:", on_click=_next)


# Formatiert eine Antwort für die Prüfseite.
def _fmt(value: object) -> str:
    """Wandelt eine Antwort in lesbaren Text um."""
    if value is None or value == []:
        return "–"
    return ", ".join(value) if isinstance(value, list) else str(value)


# Prüfseite mit allen Antworten je Schritt.
def _review() -> None:
    """Zeigt alle Antworten zur Kontrolle vor dem Absenden."""
    render_html('<div class="dt-q-head"><h2 class="dt-h2">Ihre Angaben prüfen</h2></div>'
                '<p class="dt-muted">Bitte kontrollieren Sie Ihre Antworten. Sie können jeden Schritt noch ändern.</p>')
    draft = st.session_state.q_draft
    for index, step in enumerate(STEPS):
        rows = "".join(
            f"<div><dt>{esc(q.label)}</dt><dd>{esc(_fmt(draft.get(q.field)))}</dd></div>"
            for q in step.questions if draft.get(q.field) not in (None, [])
        )
        with st.container(key=f"q_review_{index}"):
            render_html(f'<h3 class="dt-h3">{esc(step.title)}</h3><dl class="dt-dl">{rows}</dl>')
            st.button(f"{step.title} bearbeiten", key=f"q_edit_{index}", icon=":material/edit:", on_click=_goto, args=(index,))
    render_html('<p class="dt-tiny">Mit dem Absenden werden Ihre Angaben für personalisierte Empfehlungen genutzt. '
                "Sie können sie jederzeit ändern oder in den Einstellungen widerrufen.</p>")
    _nav_buttons(first=False, last=True)


# Abschlussansicht nach dem Absenden.
def _done() -> None:
    """Zeigt die Bestätigung und eine Zusammenfassung der Antworten."""
    answers = st.session_state.answers
    with st.container(key="q_done"):
        render_html(
            f'<div class="dt-success">{icon("task_alt", "ms-xl")}<div><h2 class="dt-h2">Vielen Dank, Ihr Fragebogen ist vollständig.</h2>'
            f'<p class="dt-muted">Ihr Dashboard und Ihre Angebote wurden auf Basis Ihrer Antworten aktualisiert.</p></div></div>'
        )
        rows = "".join(
            f"<div><dt>{esc(q.label)}</dt><dd>{esc(_fmt(answers.get(q.field)))}</dd></div>"
            for s in STEPS for q in s.questions if answers.get(q.field) not in (None, [])
        )
        render_html(f'<dl class="dt-dl dt-dl-2">{rows}</dl>')
        c1, c2 = st.columns(2)
        c1.button("Zu meinen Angeboten", key="q_to_offers", type="primary", icon=":material/local_offer:",
                  on_click=navigate, args=("offers",))
        c2.button("Antworten ändern", key="q_reopen", icon=":material/edit:", on_click=reopen_questionnaire)
