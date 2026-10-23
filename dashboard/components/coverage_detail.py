"""
Versicherungsdetailseite: öffnet sich nach Klick auf eine Versicherungskarte.

Aufbau von oben nach unten:
    Breadcrumb und Zurück-Link · Kunde und Versicherung mit Status · drei Kennzahlen
    · Content Enrichment (Prognosen) | Warum diese Einschätzung? + Offene Information
    · Handlungsempfehlung mit Gesprächsvorbereitung und Erinnerung

Alle Inhalte stammen aus dem Coverage-Objekt in data/mock_data.py.
"""
from __future__ import annotations

import streamlit as st

from components.customer_detail import render_conversation_guide
from components.layout import header_actions_html
from components.ui import category_class, esc, html_list, icon, render_html, status_badge
from data.mock_data import Coverage, Customer, Signal
from i18n import t, tr
from state import back_to_overview, note_question, set_reminder, toggle_guide, toggle_reason

# Anzahl der Signale, die ohne Aufklappen sichtbar sind.
VISIBLE_SIGNALS = 3


# Einstiegspunkt der Detailseite; setzt alle Bereiche in fester Reihenfolge zusammen.
def render_coverage_page(customer: Customer, coverage: Coverage, advisor: dict[str, str]) -> None:
    """Rendert die vollständige Detailseite einer Versicherung des ausgewählten Kunden."""
    render_breadcrumb(customer, coverage, advisor)
    render_coverage_header(customer, coverage)
    render_kpis(coverage)

    left, right = st.columns([1.15, 1], gap="medium")
    with left:
        render_signals(coverage)
    with right:
        render_reasons(customer, coverage)
        render_open_questions(customer, coverage)

    render_action(customer, coverage)
    if st.session_state.guide_open:
        render_conversation_guide(customer)


# ------------------------------------------------------------
# Kopfbereich: Breadcrumb, Zurück-Link, Kunde und Versicherung
# ------------------------------------------------------------

# Pfadangabe „Kunden / Name / Versicherung“ mit Benutzerbereich rechts und Zurück-Link darunter.
def render_breadcrumb(customer: Customer, coverage: Coverage, advisor: dict[str, str]) -> None:
    """Zeigt Breadcrumb, Benachrichtigungen/Benutzer und den Link zurück zur Übersicht."""
    render_html(
        f"""
        <div class="c360-topbar">
            <nav class="c360-breadcrumb" aria-label="{t("breadcrumb_aria")}">
                <span>{t("nav_customers")}</span><span class="c360-crumb-sep">/</span>
                <span>{esc(customer.name)}</span><span class="c360-crumb-sep">/</span>
                <span class="is-current" aria-current="page">{esc(coverage.label)}</span>
            </nav>
            {header_actions_html(advisor)}
        </div>
        """
    )
    st.button(
        t("back_to_overview"),
        key="back_to_overview",
        icon=":material/arrow_back:",
        on_click=back_to_overview,
    )


# Kunde links, Versicherung mit Statusanzeige rechts – ausgerichtet am Kennzahlenraster.
def render_coverage_header(customer: Customer, coverage: Coverage) -> None:
    """Zeigt Kundenprofil sowie Titel und Status der Versicherung."""
    render_html(
        f"""
        <div class="c360-covpage-head">
            <div class="c360-profile">
                <span class="c360-avatar c360-avatar-md">{icon("user")}</span>
                <div>
                    <div class="c360-covpage-name">{esc(customer.name)}</div>
                    <div class="c360-profile-meta">{t("years", n=customer.age)}<span class="c360-sep">·</span>{esc(customer.city)}<span class="c360-sep">·</span>{esc(customer.housing)}</div>
                </div>
            </div>
            <div class="c360-covpage-title-wrap">
                <span class="c360-icon-circle c360-icon-circle-xl">{icon(coverage.icon)}</span>
                <div class="c360-covpage-title" role="heading" aria-level="1">{esc(coverage.title)}</div>
                <span class="c360-status-pill c360-status-pill-{coverage.status}">{status_badge(coverage.status)}</span>
            </div>
        </div>
        """
    )


# Drei Kennzahlen-Karten (Vertragsstatus, Risikolage, Handlungsbedarf).
def render_kpis(coverage: Coverage) -> None:
    """Zeigt die Kennzahlen der Versicherung als farbige Karten mit Symbol und Text."""
    cards = "".join(
        f'<div class="c360-kpi c360-tone-{kpi.tone}">'
        f'<span class="c360-icon-circle c360-icon-circle-lg">{icon(kpi.icon)}</span>'
        f'<div><div class="c360-kpi-label">{esc(kpi.label)}</div>'
        f'<div class="c360-kpi-value">{esc(kpi.value)}</div></div></div>'
        for kpi in coverage.kpis
    )
    render_html(f'<div class="c360-kpi-grid">{cards}</div>')


# ------------------------------------------------------------
# Content Enrichment: Prognosen mit Wahrscheinlichkeiten
# ------------------------------------------------------------

# Ordnet einer Wahrscheinlichkeit einen Farbton zu (rot ab 80 %, orange ab 50 %).
def _signal_tone(probability: float) -> str:
    """Gibt den Farbton danger, warning oder info für eine Wahrscheinlichkeit zurück."""
    if probability >= 0.8:
        return "danger"
    if probability >= 0.5:
        return "warning"
    return "info"


# HTML einer Prognosezeile: Symbol, Prozentwert, Titel, Merkmale und Balken.
def _signal_html(signal: Signal) -> str:
    """Gibt das HTML einer einzelnen Prognose aus dem Content Enrichment zurück."""
    percent = round(signal.probability * 100)
    sources = '<span class="c360-sep">·</span>'.join(esc(s) for s in signal.sources)
    return (
        f'<div class="c360-signal c360-tone-{_signal_tone(signal.probability)}">'
        f'<span class="c360-icon-circle">{icon(signal.icon)}</span>'
        f'<span class="c360-signal-pct">{t("percent", n=percent)}</span>'
        f'<div class="c360-signal-body">'
        f'<div class="c360-signal-title">{esc(signal.title)}</div>'
        f'<div class="c360-signal-src">{sources}</div>'
        f'<div class="c360-bar" role="img" aria-label="{t("probability_aria", n=percent)}">'
        f'<span style="width:{percent}%"></span></div>'
        f"</div></div>"
    )


# Karte „Content Enrichment“: die wichtigsten Prognosen sichtbar, weitere aufklappbar.
def render_signals(coverage: Coverage) -> None:
    """Zeigt die Prognosen der Versicherung, sortiert nach Wahrscheinlichkeit."""
    signals = sorted(coverage.signals, key=lambda s: s.probability, reverse=True)
    visible, hidden = signals[:VISIBLE_SIGNALS], signals[VISIBLE_SIGNALS:]
    with st.container(key="enrich_panel"):
        render_html(
            f'<div class="c360-panel-title" role="heading" aria-level="2">{t("enrichment_title")}</div>'
            f'<div class="c360-panel-sub">{t("enrichment_sub")}</div>'
        )
        if not signals:
            render_html(f'<div class="c360-muted">{t("no_signals")}</div>')
            return
        render_html(f'<div class="c360-signal-list">{"".join(_signal_html(s) for s in visible)}</div>')
        if hidden:
            label = t("more_signals_one") if len(hidden) == 1 else t("more_signals_many", n=len(hidden))
            with st.expander(label):
                render_html(f'<div class="c360-signal-list">{"".join(_signal_html(s) for s in hidden)}</div>')
        render_html(
            f'<div class="c360-footnote">{icon("info", "c360-icon c360-icon-sm")}'
            f"<span>{t('probability_note')}</span></div>"
        )


# ------------------------------------------------------------
# Begründung und offene Informationen
# ------------------------------------------------------------

# Karte „Warum diese Einschätzung?“ mit aufklappbaren Gründen und Datenquellen.
def render_reasons(customer: Customer, coverage: Coverage) -> None:
    """Zeigt die Gründe der Einschätzung; ein Klick klappt die Erläuterung auf."""
    with st.container(key="why_panel"):
        render_html(f'<div class="c360-panel-title" role="heading" aria-level="2">{t("why_assessment")}</div>')
        for index, reason in enumerate(coverage.reasons):
            reason_id = f"{customer.id}_{coverage.key}_{index}"
            is_open = st.session_state.open_reason == reason_id
            detail = ""
            if is_open:
                contract = ""
                if reason.show_contract and coverage.contract:
                    rows = "".join(f"<dt>{esc(k)}</dt><dd>{esc(v)}</dd>" for k, v in coverage.contract.items())
                    contract = f'<dl class="c360-dl c360-dl-inline">{rows}</dl>'
                text = f"<div>{esc(reason.detail)}</div>" if reason.detail else ""
                detail = f'<div class="c360-reason-detail">{text}{contract}</div>'
            with st.container(key=f"reasoncard_{reason_id}"):
                render_html(
                    f"""
                    <div class="c360-reason-row{" is-open" if is_open else ""}">
                        <div class="c360-reason-main">
                            <span class="c360-icon-circle">{icon(reason.icon)}</span>
                            <div class="c360-reason-text">
                                <div class="c360-reason-title">{esc(reason.title)}</div>
                                <div class="c360-reason-summary">{esc(reason.summary)}</div>
                            </div>
                            {icon("chevron_right", "c360-icon c360-chevron")}
                        </div>
                        {detail}
                    </div>
                    """
                )
                st.button(
                    t("reason_hide" if is_open else "reason_show", title=tr(reason.title)),
                    key=f"reasonpick_{reason_id}",
                    on_click=toggle_reason,
                    args=(reason_id,),
                )
        with st.container(key="consent_box"):
            with st.expander(t("sources_consent"), icon=":material/open_in_new:"):
                render_html(
                    f"""
                    <div class="c360-why">
                        <div class="c360-label">{t("sources_used")}</div>
                        {html_list(coverage.sources)}
                        <div class="c360-label c360-mt">{t("consent")}</div>
                        <div>{esc(coverage.consent)}</div>
                    </div>
                    """
                )


# Karte „Offene Information“: Fragen, die im Gespräch geklärt werden sollten.
def render_open_questions(customer: Customer, coverage: Coverage) -> None:
    """Zeigt offene Fragen mit Button zum Vormerken für das Kundengespräch."""
    questions = coverage.open_questions
    title = t("open_info_one") if len(questions) == 1 else t("open_info_many")
    with st.container(key="open_panel"):
        render_html(f'<div class="c360-panel-title" role="heading" aria-level="2">{title}</div>')
        if not questions:
            render_html(f'<div class="c360-muted">{t("no_open_points")}</div>')
            return
        for index, question in enumerate(questions):
            question_id = f"{customer.id}|{coverage.key}|{index}"
            noted = question_id in st.session_state.noted_questions
            text_col, button_col = st.columns([1.7, 1], vertical_alignment="center")
            with text_col:
                render_html(
                    f'<div class="c360-question"><span class="c360-question-icon">?</span>'
                    f"<span>{esc(question)}</span></div>"
                )
            with button_col:
                st.button(
                    t("noted") if noted else t("clarify_in_conversation"),
                    key=f"note_{customer.id}_{coverage.key}_{index}",
                    icon=":material/check:" if noted else None,
                    disabled=noted,
                    on_click=note_question,
                    args=(question_id,),
                )


# ------------------------------------------------------------
# Handlungsempfehlung
# ------------------------------------------------------------

# Farbiges Band mit Empfehlung, Kundennutzen, Gesprächsvorbereitung und Erinnerung.
def render_action(customer: Customer, coverage: Coverage) -> None:
    """Zeigt die Handlungsempfehlung zur Versicherung mit den nächsten Schritten."""
    tone = coverage.action_category or "neutral"
    reminder_id = f"{customer.id}|{coverage.key}"
    has_reminder = reminder_id in st.session_state.reminders
    with st.container(key=f"actbox_{tone}"):
        left, right = st.columns([1.5, 1], gap="medium")
        with left:
            render_html(
                f"""
                <div class="c360-reco-head c360-action {category_class(tone)}">
                    <span class="c360-icon-circle c360-icon-circle-lg">{icon(coverage.action_icon)}</span>
                    <div>
                        <div class="c360-action-kicker">{t("action_recommendation")}</div>
                        <div class="c360-reco-title" role="heading" aria-level="2">{esc(coverage.action_title)}</div>
                        <div class="c360-action-text">{esc(coverage.recommendation)}</div>
                    </div>
                </div>
                """
            )
        with right, st.container(key="act_side"):
            with st.container(key="how_box"):
                with st.popover(t("how_title")):
                    render_html(
                        f"""
                        <div class="c360-why">
                            <div class="c360-why-title">{t("how_heading")}</div>
                            <ol class="c360-list">
                                <li>{t("how_step1")}</li>
                                <li>{t("how_step2")}</li>
                                <li>{t("how_step3")}</li>
                            </ol>
                            <div class="c360-note">{t("how_note")}</div>
                        </div>
                        """
                    )
            if coverage.benefit:
                render_html(
                    f'<div class="c360-benefit {category_class(tone)}">{icon("shield", "c360-icon c360-icon-sm")}'
                    f"<span>{t('customer_benefit', text=esc(coverage.benefit))}</span></div>"
                )
            prep_col, remind_col = st.columns([1.35, 1], vertical_alignment="center")
            with prep_col:
                st.button(
                    t("close_preparation") if st.session_state.guide_open else t("prepare_conversation"),
                    key=f"covguide_{customer.id}_{coverage.key}",
                    type="primary",
                    icon=":material/description:",
                    on_click=toggle_guide,
                )
            with remind_col:
                st.button(
                    t("reminder_set") if has_reminder else t("remind_later"),
                    key=f"remind_{customer.id}_{coverage.key}",
                    icon=":material/check:" if has_reminder else ":material/schedule:",
                    disabled=has_reminder,
                    on_click=set_reminder,
                    args=(reminder_id,),
                )
