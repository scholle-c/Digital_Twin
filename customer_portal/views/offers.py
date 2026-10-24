"""
Individuelle Angebote: begründete Empfehlungen aus Digital Twin, Profil und Fragebogen.

Jede Karte zeigt Bedarf, Leistungen, Begründung, Herkunft und einen ausdrücklich als
Beispiel gekennzeichneten Preis. Angebote können angesehen, angefragt oder ausgeblendet werden.
"""
from __future__ import annotations

import streamlit as st

from core.personalization import CATEGORY_LABELS
from core.state import dismiss_offer, navigate, request_offer, restore_offers, toggle_offer
from ui.components import badge, empty_state, esc, icon, page_header, render_html

CATEGORY_TONES = {"prevention": "danger", "gap": "warn", "retention": "warn", "cross_sell": "ok"}
FILTERS = {"Alle": None, "Prävention": "prevention", "Lücken schließen": "gap", "Ergänzungen": "cross_sell"}


# Baut die Angebotsseite auf.
def render(ctx: dict) -> None:
    """Rendert Erklärung, Filter und Angebotskarten."""
    page_header("Individuelle Angebote", "Empfehlungen auf Basis Ihres Profils, Ihrer Antworten und Ihres Digital Twin.", "local_offer")
    with st.expander("Wie entstehen diese Empfehlungen?", icon=":material/help:"):
        render_html(
            '<ol class="dt-list"><li><b>Digital Twin:</b> schätzt Risiken (z. B. Brand, Hochwasser) und Lebensereignisse '
            "aus Ihren Wohn- und Vertragsdaten.</li><li><b>Profil & Fragebogen:</b> ergänzen Familie, Mobilität und Ihre "
            "Prioritäten.</li><li><b>Reihenfolge:</b> Prävention vor Lücken vor Ergänzungen.</li></ol>"
            '<p class="dt-tiny">Empfehlungen sind Vorschläge und keine Garantie, dass ein Produkt zu Ihnen passt. '
            "Preise sind Beispielwerte; das verbindliche Angebot erhalten Sie nach individueller Beratung.</p>"
        )
    if not ctx["personalized"]:
        render_html(f'<div class="dt-callout dt-callout-warn">{icon("lock", "ms-sm")}<span>Sie haben personalisierte '
                    f"Empfehlungen in den Einstellungen deaktiviert. Deshalb zeigen wir keine individuellen Angebote.</span></div>")
        st.button("Einstellungen öffnen", key="offers_to_settings", icon=":material/settings:", on_click=navigate, args=("settings",))
        return
    if not st.session_state.q_submitted:
        with st.container(key="offer_q_hint"):
            render_html(f'<div class="dt-callout">{icon("assignment", "ms-sm")}<span><b>Noch genauer:</b> Mit dem '
                        f"Fragebogen (ca. 3 Minuten) berücksichtigen wir Mobilität, Wohneigentum und Ihre Prioritäten.</span></div>")
            st.button("Fragebogen starten", key="offers_to_q", icon=":material/arrow_forward:", on_click=navigate, args=("questionnaire",))

    offers = ctx["offers"]
    choice = st.radio("Kategorie", list(FILTERS), horizontal=True, key="offer_filter", label_visibility="collapsed")
    shown = [o for o in offers if FILTERS[choice] in (None, o.product.category)]
    dismissed = len(st.session_state.dismissed_offers)

    if not shown:
        empty_state("Keine Angebote in dieser Ansicht",
                    "Sie haben alle Empfehlungen bearbeitet – oder es passt gerade nichts zu Ihrer Situation.", "check_circle")
    columns = st.columns(2, gap="medium")
    for index, offer in enumerate(shown):
        with columns[index % 2]:
            _offer_card(offer)
    if dismissed:
        st.button(f"{dismissed} ausgeblendete Angebote wieder anzeigen", key="restore_offers",
                  icon=":material/visibility:", on_click=restore_offers)


# Karte eines Angebots inkl. aufklappbarer Details und Aktionen.
def _offer_card(offer) -> None:
    """Rendert eine Angebotskarte."""
    product = offer.product
    is_open = st.session_state.open_offer == product.id
    requested = product.id in st.session_state.requested_offers
    sources = " · ".join(dict.fromkeys(offer.sources))
    status = badge("Angefragt", "info", "schedule") if requested else ""
    benefits = "".join(f"<li>{icon('check', 'ms-sm')}{esc(b)}</li>" for b in product.benefits)
    with st.container(key=f"offer_{product.id}"):
        render_html(
            f"""
            <div class="dt-offer">
                <div class="dt-offer-top">
                    <span class="dt-offer-icon dt-tone-{CATEGORY_TONES[product.category]}">{icon(product.icon)}</span>
                    <div class="dt-grow">{badge(CATEGORY_LABELS[product.category], CATEGORY_TONES[product.category])}
                    <div class="dt-offer-name">{esc(product.name)}</div></div>{status}
                </div>
                <p class="dt-offer-need">{esc(product.need)}</p>
                <div class="dt-offer-why">{icon("lightbulb", "ms-sm")}<span><b>Warum für Sie:</b> {esc(offer.reason)}</span></div>
                <ul class="dt-benefits">{benefits}</ul>
                <div class="dt-offer-foot"><span class="dt-price">{esc(product.price)}</span>
                <span class="dt-tiny">Beispielwert · unverbindlich</span></div>
                <div class="dt-source">{icon("hub", "ms-sm")}Quelle: {esc(sources)}</div>
            </div>
            """
        )
        view_col, dismiss_col = st.columns([1.4, 1])
        view_col.button("Details schließen" if is_open else "Angebot ansehen", key=f"offerview_{product.id}",
                        type="primary", icon=":material/visibility:", on_click=toggle_offer, args=(product.id,))
        dismiss_col.button("Nicht relevant", key=f"offerdismiss_{product.id}", icon=":material/close:",
                           on_click=dismiss_offer, args=(product.id,))
        if is_open:
            render_html(
                f'<div class="dt-offer-detail"><h4 class="dt-h4">So könnte Ihr Schutz aussehen</h4>'
                f'<p>{esc(product.need)} Ihre Beraterin bzw. Ihr Berater erstellt Ihnen ein individuelles, '
                f"unverbindliches Angebot und prüft gemeinsam mit Ihnen, ob es wirklich passt.</p></div>"
            )
            st.button("Bereits angefragt" if requested else "Unverbindlich anfragen", key=f"offerreq_{product.id}",
                      icon=":material/send:", disabled=requested, on_click=request_offer, args=(product.id, product.name))
