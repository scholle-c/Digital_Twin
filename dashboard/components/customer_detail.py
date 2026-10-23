"""
Kundendetailansicht (rechte Spalte): Profil, wichtigste Empfehlung,
Gesprächsvorbereitung, aktuelle Absicherung und Ereignis-Timeline.

Alle Inhalte stammen aus dem übergebenen Customer-Objekt. Ein Kundenwechsel
in der Liste aktualisiert diesen Bereich daher automatisch.
"""
from __future__ import annotations

import streamlit as st

from components.twin_view import render_twin_comparison
from components.ui import category_class, esc, html_list, icon, render_html, status_badge
from data.mock_data import Customer
from i18n import t, tr
from state import open_coverage, toggle_guide


# Einstiegspunkt der Detailansicht; setzt die Bereiche in fester Reihenfolge zusammen.
def render_customer_detail(customer: Customer) -> None:
    """Rendert alle Bereiche der Detailansicht für den ausgewählten Kunden."""
    with st.container(key="detail_panel"):
        render_customer_header(customer)
        tab = st.segmented_control(
            t("detail_tabs"),
            options=["overview", "twin"],
            format_func=lambda key: t(f"tab_{key}"),
            key="detail_tab",
            label_visibility="collapsed",
        )
        if tab == "twin":
            render_twin_comparison(customer.id)
            return
        render_recommendation(customer)
        if st.session_state.guide_open:
            render_conversation_guide(customer)
        render_coverage_cards(customer)
        render_timeline(customer)


# ------------------------------------------------------------
# Kundenprofil und Begründung („Warum sehe ich das?“)
# ------------------------------------------------------------

# Profilzeile mit Avatar, Name und Eckdaten; rechts letzter Kontakt und Erklärung.
def render_customer_header(customer: Customer) -> None:
    """Zeigt Name, Alter, Ort und Wohnsituation sowie die Herkunft der Empfehlung."""
    with st.container(key="profile_row"):
        left, right = st.columns([1.5, 1], vertical_alignment="top")
        with left:
            render_html(
                f"""
                <div class="c360-profile">
                    <span class="c360-avatar">{icon("user")}</span>
                    <div>
                        <div class="c360-profile-name" role="heading" aria-level="2">{esc(customer.name)}</div>
                        <div class="c360-profile-meta">{t("years", n=customer.age)}<span class="c360-sep">·</span>{esc(customer.city)}<span class="c360-sep">·</span>{esc(customer.housing)}</div>
                    </div>
                </div>
                """
            )
        with right:
            render_html(
                f'<div class="c360-meta-line">{icon("map_pin")}'
                f"<span>{t('last_contact', date=esc(customer.last_contact))}</span></div>"
            )
            # Der Expander ersetzt den Link „Warum sehe ich das?“ und erklärt die Datenbasis.
            with st.container(key="why_box"):
                with st.expander(t("why_see_this"), icon=":material/help_outline:"):
                    render_html(
                        f"""
                        <div class="c360-why">
                            <div class="c360-why-title">{t("why_title")}</div>
                            {html_list(customer.explanation)}
                            <div class="c360-note">{icon("info", "c360-icon c360-icon-sm")}<span>{t("why_note")}</span></div>
                        </div>
                        """
                    )
            render_html(f'<div class="c360-sources">{" · ".join(esc(s) for s in customer.sources)}</div>')


# ------------------------------------------------------------
# Hauptempfehlung „Das Wichtigste jetzt“
# ------------------------------------------------------------

# Große Empfehlungskarte; Farbe richtet sich nach der Kategorie des Kunden.
def render_recommendation(customer: Customer) -> None:
    """Zeigt Situation, Empfehlung, Kundennutzen und den Button zur Gesprächsvorbereitung."""
    situation = "".join(f"<span>{esc(line)}</span>" for line in customer.situation)
    with st.container(key=f"reco_box_{customer.category}"):
        left, right = st.columns([1.7, 1], gap="medium")
        with left:
            render_html(
                f"""
                <div class="c360-reco {category_class(customer.category)}">
                    <div class="c360-reco-head">
                        <span class="c360-icon-circle c360-icon-circle-lg">{icon(customer.topic_icon)}</span>
                        <div>
                            <div class="c360-kicker">{t("most_important_now")}</div>
                            <div class="c360-reco-title" role="heading" aria-level="2">{esc(customer.headline)}</div>
                        </div>
                    </div>
                    <div class="c360-reco-text">{situation}</div>
                </div>
                """
            )
        with right:
            render_html(
                f"""
                <div class="c360-reco-side {category_class(customer.category)}">
                    <div class="c360-side-title">{t("recommendation")}</div>
                    <div class="c360-side-text">{esc(customer.recommendation)}</div>
                    <div class="c360-benefit">{icon("shield", "c360-icon c360-icon-sm")}<span>{t("customer_benefit", text=esc(customer.benefit))}</span></div>
                </div>
                """
            )
            label = t("close_preparation") if st.session_state.guide_open else t("prepare_conversation")
            st.button(
                label,
                key=f"guide_toggle_{customer.id}",
                type="primary",
                icon=":material/description:",
                on_click=toggle_guide,
            )


# ------------------------------------------------------------
# Gesprächsvorbereitung
# ------------------------------------------------------------

# Erscheint unter der Empfehlung, sobald „Gespräch vorbereiten“ geklickt wurde.
def render_conversation_guide(customer: Customer) -> None:
    """Zeigt Gesprächseinstieg, mögliche und vorgemerkte Fragen sowie das Ziel des Gesprächs."""
    # Fragen, die auf einer Versicherungsdetailseite mit „Im Gespräch klären“ vorgemerkt wurden.
    noted = [
        question
        for coverage in customer.coverages
        for index, question in enumerate(coverage.open_questions)
        if f"{customer.id}|{coverage.key}|{index}" in st.session_state.noted_questions
    ]
    questions = customer.conversation_questions + noted
    with st.container(key="guide_box"):
        render_html(
            f"""
            <div class="c360-guide">
                <div class="c360-guide-title" role="heading" aria-level="3">{icon("file")}<span>{t("guide_title", name=esc(customer.name))}</span></div>
                <div class="c360-guide-grid">
                    <div>
                        <div class="c360-label">{t("guide_opening")}</div>
                        <blockquote class="c360-quote">{t("quote", text=esc(customer.conversation_opening))}</blockquote>
                    </div>
                    <div>
                        <div class="c360-label">{t("guide_questions")}</div>
                        {html_list(questions, ordered=True)}
                    </div>
                </div>
                <div class="c360-goal">{icon("target", "c360-icon c360-icon-sm")}<span><strong>{t("guide_goal")}</strong> {esc(customer.conversation_goal)}</span></div>
            </div>
            """
        )


# ------------------------------------------------------------
# Aktuelle Absicherung
# ------------------------------------------------------------

# Zeile mit klickbaren Versicherungskarten; ein Klick öffnet die Versicherungsdetailseite.
def render_coverage_cards(customer: Customer) -> None:
    """Zeigt alle Versicherungssparten des Kunden als klickbare Statuskarten."""
    render_html(f'<div class="c360-section-title" role="heading" aria-level="3">{t("current_coverage")}</div>')
    columns = st.columns(len(customer.coverages), gap="small")
    for column, coverage in zip(columns, customer.coverages):
        with column:
            with st.container(key=f"covcard_{customer.id}_{coverage.key}"):
                render_html(
                    f"""
                    <div class="c360-cov-card c360-cov-{coverage.status}">
                        <span class="c360-icon-circle">{icon(coverage.icon)}</span>
                        <div>
                            <div class="c360-cov-label">{esc(coverage.label)}</div>
                            {status_badge(coverage.status)}
                        </div>
                        {icon("chevron_right", "c360-icon c360-chevron c360-cov-chevron")}
                    </div>
                    """
                )
                st.button(
                    t("open_coverage", label=tr(coverage.label)),
                    key=f"covpick_{customer.id}_{coverage.key}",
                    on_click=open_coverage,
                    args=(coverage.key,),
                )


# ------------------------------------------------------------
# Neue Ereignisse
# ------------------------------------------------------------

# Schlichte vertikale Timeline ohne Diagrammbibliothek; neue Ereignisse erhalten einen roten Punkt.
def render_timeline(customer: Customer) -> None:
    """Zeigt die Ereignisse des Kunden als vertikale Zeitleiste."""
    items = ""
    for event in customer.events:
        new_class = " is-new" if event.is_new else ""
        new_label = f'<span class="c360-new-label">{t("new")}</span>' if event.is_new else ""
        items += (
            f'<li class="c360-tl-item{new_class}">'
            f'<span class="c360-tl-dot"></span>'
            f'<span class="c360-icon-circle c360-icon-circle-sm">{icon(event.icon)}</span>'
            f'<span><strong>{esc(event.when)}</strong><span class="c360-sep">·</span>{esc(event.title)}</span>'
            f"{new_label}</li>"
        )
    render_html(
        f'<div class="c360-section-title" role="heading" aria-level="3">{t("new_events")}</div>'
        f'<ol class="c360-timeline">{items}</ol>'
    )
