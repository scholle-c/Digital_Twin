"""
Meine Versicherungen: Gesamtüberblick, Filter nach Status und Detailansicht je Vertrag.

Hinweis im Prototyp: Leistungsangaben sind Beispielwerte und keine verbindliche Deckungsauskunft.
"""
from __future__ import annotations

import streamlit as st

from core.data import POLICY_STATUS, TODAY
from core.state import navigate, toggle_policy
from ui.components import badge, empty_state, esc, euro, icon, page_header, render_html, stat_tile
from ui.layout import policy_badge

FILTERS = {"Alle": None, "Aktiv": "active", "Prüfung empfohlen": "review"}


# Baut die Vertragsseite auf.
def render(ctx: dict) -> None:
    """Rendert Überblick, Filter und Vertragskarten."""
    policies = ctx["policies"]
    page_header("Meine Versicherungen", "Alle Verträge auf einen Blick – mit Status und Details.", "verified_user")

    active = [p for p in policies if p.status in ("active", "review")]
    review = [p for p in policies if p.status == "review"]
    soon = [p for p in policies if p.renewal and 0 <= (p.renewal - TODAY).days <= 60]
    render_html(
        '<div class="dt-stat-grid dt-stat-grid-4">'
        + stat_tile("Verträge", str(len(active)), "description", "aktiv", "info")
        + stat_tile("Monatsbeitrag gesamt", euro(sum(p.premium_month for p in active)), "payments", "Beispielwerte", "info")
        + stat_tile("Prüfung empfohlen", str(len(review)), "error", "siehe Hinweise", "warn" if review else "ok")
        + stat_tile("Verlängerung ≤ 60 Tage", str(len(soon)), "event", ", ".join(p.name for p in soon) or "keine", "info")
        + "</div>"
    )

    choice = st.radio("Filter", list(FILTERS), horizontal=True, key="policyfilter", label_visibility="collapsed")
    shown = [p for p in policies if FILTERS[choice] in (None, p.status)]
    if not shown:
        empty_state("Keine Verträge in dieser Ansicht", "Wählen Sie einen anderen Filter.", "filter_alt_off")
        return

    columns = st.columns(2, gap="medium")
    for index, policy in enumerate(shown):
        with columns[index % 2]:
            _policy_card(policy)

    render_html(
        f'<p class="dt-tiny">{icon("gavel", "ms-sm")} Die Angaben dienen nur der Veranschaulichung im Prototyp '
        f"und stellen keine rechtsverbindliche Deckungsauskunft dar. Maßgeblich sind allein Ihre Vertragsunterlagen.</p>"
    )


# Karte eines Vertrags; aufgeklappt mit Leistungsübersicht, Hinweisen und Dokumenten.
def _policy_card(policy) -> None:
    """Rendert die Karte und ggf. die Detailansicht eines Vertrags."""
    is_open = st.session_state.open_policy == policy.id
    renewal = f"{policy.renewal:%d.%m.%Y}" if policy.renewal else "laufend"
    with st.container(key=f"policy_{policy.id}"):
        render_html(
            f"""
            <div class="dt-policy {'is-review' if policy.status == 'review' else ''}">
                <div class="dt-policy-top">
                    <span class="dt-policy-icon">{icon(policy.icon)}</span>
                    <div class="dt-grow"><div class="dt-policy-name">{esc(policy.name)}</div>
                    <div class="dt-muted">{esc(policy.product_line)} · Nr. {esc(policy.policy_number)}</div></div>
                    {policy_badge(policy.status, POLICY_STATUS)}
                </div>
                <div class="dt-policy-facts">
                    <div><small>Beginn</small><b>{policy.start:%d.%m.%Y}</b></div>
                    <div><small>Verlängerung</small><b>{renewal}</b></div>
                    <div><small>Beitrag</small><b>{euro(policy.premium_month)} / Monat</b></div>
                </div>
            </div>
            """
        )
        if policy.status == "review":
            render_html(f'<div class="dt-callout dt-callout-warn">{icon("error", "ms-sm")}<span>{esc(policy.review_note)}</span></div>')
        st.button(
            "Details schließen" if is_open else "Details ansehen", key=f"policybtn_{policy.id}",
            icon=":material/expand_less:" if is_open else ":material/expand_more:",
            on_click=toggle_policy, args=(policy.id,),
        )
        if is_open:
            rows = "".join(f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>" for k, v in policy.coverage.items())
            docs = "".join(f"<li>{icon('picture_as_pdf', 'ms-sm')}{esc(d)} {badge('Demo', 'neutral')}</li>" for d in policy.documents)
            render_html(
                f'<div class="dt-policy-detail"><h4 class="dt-h4">Leistungsübersicht (Beispiel)</h4>'
                f'<div class="dt-table-wrap"><table class="dt-table">{rows}</table></div>'
                f'<h4 class="dt-h4">Dokumente</h4><ul class="dt-doc-list">{docs}</ul></div>'
            )
            if policy.status == "review":
                st.button("Passende Angebote ansehen", key=f"policyoffers_{policy.id}", type="primary",
                          icon=":material/local_offer:", on_click=navigate, args=("offers",))
