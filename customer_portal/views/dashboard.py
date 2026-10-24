"""
Übersicht (Dashboard): Absicherungsgrad, Vertragsstatus, nächste Schritte,
Verträge, Mitteilungen, persönliche Risiken und Schnellzugriffe.

Alle Inhalte werden aus dem Kontext berechnet; Profil- und Fragebogenänderungen
wirken sich daher sofort aus.
"""
from __future__ import annotations

from datetime import datetime

import streamlit as st

from core.data import POLICY_STATUS, TODAY, region_insights
from core.personalization import CATEGORY_LABELS
from core.state import navigate, open_notification
from ui.components import badge, coverage_ring, esc, euro, icon, page_header, render_html, stat_tile
from ui.layout import card_head, policy_badge

CATEGORY_TONES = {"prevention": "danger", "gap": "warn", "cross_sell": "ok"}


# Öffnet die Angebotsseite direkt mit aufgeklapptem Angebot.
def _open_offer(product_id: str) -> None:
    """Navigiert zu den Angeboten und klappt das gewählte Angebot auf."""
    navigate("offers")
    st.session_state.open_offer = product_id


# Begrüßung passend zur Tageszeit.
def _greeting() -> str:
    """Gibt „Guten Morgen“, „Guten Tag“ oder „Guten Abend“ zurück."""
    hour = datetime.now().hour
    return "Guten Morgen" if hour < 11 else "Guten Tag" if hour < 18 else "Guten Abend"


# Baut das Dashboard aus dem Kontext auf.
def render(ctx: dict) -> None:
    """Rendert die Startseite des Kundenportals."""
    profile, policies, offers = ctx["profile"], ctx["policies"], ctx["offers"]
    review = [p for p in policies if p.status == "review"]
    page_header(
        f"{_greeting()}, {profile['first_name']}!",
        f"{len(review)} {'Vertrag' if len(review) == 1 else 'Verträge'} zur Prüfung · "
        f"{len(offers)} persönliche {'Empfehlung' if len(offers) == 1 else 'Empfehlungen'} · Stand {TODAY:%d.%m.%Y}",
    )

    left, right = st.columns([1, 1.7], gap="medium")
    with left, st.container(key="card_coverage"):
        _coverage_card(ctx)
    with right, st.container(key="card_status"):
        _status_card(ctx, review)

    col_a, col_b, col_c = st.columns(3, gap="medium")
    with col_a, st.container(key="card_policies"):
        _policies_card(policies)
    with col_b, st.container(key="card_notes"):
        _notifications_card()
    with col_c, st.container(key="card_risks"):
        _risk_card(ctx)

    _shortcuts(ctx)


# Ring mit Absicherungsgrad und Liste der Bedarfsfelder.
def _coverage_card(ctx: dict) -> None:
    """Zeigt, wie gut der Kunde insgesamt abgesichert ist."""
    card_head("Ihr Absicherungsgrad", badge("Schätzung", "neutral", "info"))
    rows = ""
    for need in ctx["needs"]:
        state = ("Abgedeckt", "ok", "check_circle") if need.covered == 1 else \
            ("Teilweise", "warn", "error") if need.covered > 0 else ("Offen", "danger", "cancel")
        rows += (
            f'<li><span><b>{esc(need.label)}</b><small>{esc(need.hint)}</small></span>{badge(state[0], state[1], state[2])}</li>'
        )
    render_html(
        f'<div class="dt-coverage">{coverage_ring(ctx["score"], "abgesichert")}'
        f'<ul class="dt-need-list">{rows}</ul></div>'
        f'<p class="dt-tiny">Gewichtete Einschätzung aus Verträgen, Profil und Fragebogen – keine verbindliche Bedarfsanalyse.</p>'
    )


# Kennzahlen zum Vertragsstand und die wichtigsten nächsten Schritte.
def _status_card(ctx: dict, review: list) -> None:
    """Zeigt Kennzahlen und priorisierte nächste Schritte."""
    policies = ctx["policies"]
    active = [p for p in policies if p.status in ("active", "review")]
    renewals = sorted(p.renewal for p in policies if p.renewal and p.renewal >= TODAY)
    card_head("Ihr Versicherungsstatus")
    render_html(
        '<div class="dt-stat-grid">'
        + stat_tile("Aktive Verträge", str(len(active)), "verified_user", "inkl. zu prüfender", "info")
        + stat_tile("Prüfung empfohlen", str(len(review)), "error", "Details unter Verträge", "warn" if review else "ok")
        + stat_tile("Monatsbeitrag", euro(sum(p.premium_month for p in active)), "payments", "alle Verträge", "info")
        + stat_tile("Nächste Verlängerung", f"{renewals[0]:%d.%m.%Y}" if renewals else "–", "event", "", "info")
        + "</div>"
    )
    render_html('<h3 class="dt-h3 dt-mt">Ihre nächsten Schritte</h3>')
    steps = ctx["offers"][:3]
    if not st.session_state.q_submitted:
        with st.container(key="step_questionnaire"):
            render_html(
                f'<div class="dt-step">{icon("assignment")}<div><b>Fragebogen ausfüllen</b>'
                f"<small>3 Minuten – macht Ihre Empfehlungen genauer</small></div></div>"
            )
            st.button("Starten", key="stepbtn_questionnaire", on_click=navigate, args=("questionnaire",))
    with st.container(key="step_move"):
        render_html(
            f'<div class="dt-step">{icon("moving")}<div><b>Umzug geplant? Orte vergleichen</b>'
            f"<small>Sicherheit, Nachbarschaft und Risiken für Ihren Wunschort prüfen</small></div></div>"
        )
        st.button("Orte prüfen", key="stepbtn_move", on_click=navigate, args=("trends",))
    if not steps:
        render_html('<p class="dt-muted">Aktuell gibt es keine offenen Empfehlungen. Gut abgesichert!</p>')
    for offer in steps:
        cat = offer.product.category
        with st.container(key=f"step_{offer.product.id}"):
            render_html(
                f'<div class="dt-step">{icon(offer.product.icon)}<div><b>{esc(offer.product.name)}</b>'
                f"<small>{esc(offer.reason)}</small></div>{badge(CATEGORY_LABELS[cat], CATEGORY_TONES[cat])}</div>"
            )
            st.button("Ansehen", key=f"stepbtn_{offer.product.id}", on_click=_open_offer, args=(offer.product.id,))


# Kompakte Vertragsliste mit Status.
def _policies_card(policies: list) -> None:
    """Zeigt alle Verträge mit Statusbadge und Link zur Vertragsseite."""
    card_head("Meine Verträge")
    rows = "".join(
        f'<li>{icon(p.icon)}<span>{esc(p.name)}</span>{policy_badge(p.status, POLICY_STATUS)}</li>' for p in policies
    )
    render_html(f'<ul class="dt-mini-list">{rows}</ul>')
    st.button("Alle Verträge ansehen", key="dash_all_policies", icon=":material/arrow_forward:",
              on_click=navigate, args=("insurance",))


# Die drei neuesten Mitteilungen.
def _notifications_card() -> None:
    """Zeigt die neuesten Mitteilungen; ein Klick öffnet die zugehörige Seite."""
    notes = st.session_state.notifications
    card_head("Mitteilungen", badge(f"{sum(not n['read'] for n in notes)} neu", "info") if notes else "")
    if not notes:
        render_html('<p class="dt-muted">Keine Mitteilungen.</p>')
    for note in notes[:3]:
        with st.container(key=f"dnote_{note['id']}"):
            dot = '<span class="dt-dot" aria-label="ungelesen"></span>' if not note["read"] else ""
            render_html(
                f'<div class="dt-note-row">{dot}<div><b>{esc(note["title"])}</b>'
                f'<small>{note["date"]:%d.%m.%Y}</small></div></div>'
            )
            st.button("Öffnen", key=f"dnotebtn_{note['id']}", on_click=open_notification, args=(note["id"],))
    st.button("Alle Mitteilungen", key="dash_all_notes", icon=":material/arrow_forward:",
              on_click=navigate, args=("notifications",))


# Persönliche Risiken aus dem Digital Twin als schlichte Balken.
def _risk_card(ctx: dict) -> None:
    """Zeigt die Risikoeinschätzung des Digital Twin für den Kunden."""
    card_head("Ihre Risiken", badge("Modellschätzung", "neutral", "insights"))
    twin = ctx["twin"]
    if not twin:
        render_html('<p class="dt-muted">Die Risikoeinschätzung ist gerade nicht verfügbar.</p>')
    else:
        top = max((p for _, _, p, _, _ in twin.risks), default=0.01) or 0.01
        rows = ""
        for _, label, p, damage, drivers in sorted(twin.risks, key=lambda r: -r[2]):
            driver = f" · {esc(', '.join(drivers))}" if drivers else ""
            rows += (
                f'<li><div class="dt-bar-row"><span>{esc(label)}</span><b>{p:.1%}</b></div>'
                f'<div class="dt-bar"><span style="width:{max(4, round(100 * p / top))}%"></span></div>'
                f"<small>Ø erwarteter Schaden {euro(damage, 0)} pro Jahr{driver}</small></li>"
            )
        render_html(f'<ul class="dt-risk-list">{rows}</ul>'
                    '<p class="dt-tiny">Wahrscheinlichkeit für die nächsten 12 Monate.</p>')
    st.button("Zu Trends & Analysen", key="dash_trends", icon=":material/arrow_forward:", on_click=navigate, args=("trends",))


# Kurzer Teaser zur Region für die Schnellzugriff-Kachel, z. B. „Sichere Gegend · 52 % Singles“.
def _region_teaser(profile: dict) -> str:
    """Fasst die wichtigsten Regionsaussagen in einer Zeile zusammen."""
    try:
        r = region_insights(profile)
    except Exception:  # noqa: BLE001
        return "Risiken in Ihrer Region"
    parts = []
    if r["crime_all"] and r["crime_region"] <= r["crime_all"] * 0.85:
        parts.append("Sichere Gegend")
    if r["singles"] >= 0.45:
        parts.append(f"{r['singles']:.0%} Singles")
    if r["same_age"] >= 0.3:
        parts.append("viele in Ihrem Alter")
    return " · ".join(parts) or "Risiken und Umfeld in Ihrer Region"


# Schnellzugriffe als große Kacheln.
def _shortcuts(ctx: dict) -> None:
    """Zeigt Schnellzugriffe zu Profil, Fragebogen, Angeboten und Analysen."""
    render_html('<h2 class="dt-h2 dt-mt">Schnellzugriff</h2>')
    items = [
        ("profile", "Profil verwalten", "person", "Kontakt, Familie, Präferenzen"),
        ("questionnaire", "Fragebogen", "assignment", "Erledigt ✓" if st.session_state.q_submitted else "Noch offen"),
        ("offers", "Angebote", "local_offer", f"{len(ctx['offers'])} {'Empfehlung' if len(ctx['offers']) == 1 else 'Empfehlungen'}"),
        ("trends", "Meine Region", "insights", _region_teaser(ctx["profile"])),
    ]
    columns = st.columns(len(items), gap="small")
    for column, (page, title, sym, hint) in zip(columns, items):
        with column, st.container(key=f"tile_{page}"):
            render_html(f'<div class="dt-tile">{icon(sym, "ms-lg")}<b>{esc(title)}</b><small>{esc(hint)}</small></div>')
            st.button(f"{title} öffnen", key=f"tilebtn_{page}", on_click=navigate, args=(page,))
