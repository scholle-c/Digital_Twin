"""
Mitteilungen: Warnungen, Vertragsinfos und Bestätigungen mit Filter und Gelesen-Status.
"""
from __future__ import annotations

import streamlit as st

from core.state import mark_all_read, open_notification
from ui.components import badge, empty_state, esc, icon, page_header, render_html

CATEGORIES = {
    "warning": ("Warnung", "warning", "danger"),
    "contract": ("Vertrag", "description", "info"),
    "offer": ("Angebot", "local_offer", "ok"),
    "system": ("Hinweis", "info", "neutral"),
}


# Baut die Mitteilungsseite auf.
def render(ctx: dict) -> None:
    """Rendert Filter und Mitteilungsliste."""
    page_header("Mitteilungen", "Wichtige Hinweise zu Ihren Verträgen und Ihrer Region.", "notifications")
    notes = st.session_state.notifications
    unread = sum(not n["read"] for n in notes)
    f_col, a_col = st.columns([2, 1], vertical_alignment="center")
    only_unread = f_col.toggle(f"Nur ungelesene anzeigen ({unread})", key="notes_unread")
    a_col.button("Alle als gelesen markieren", key="notes_all_read", icon=":material/done_all:",
                 on_click=mark_all_read, disabled=unread == 0)
    shown = [n for n in notes if not (only_unread and n["read"])]
    if not shown:
        empty_state("Alles gelesen", "Sie haben keine ungelesenen Mitteilungen.", "notifications_off")
        return
    for note in shown:
        label, sym, tone = CATEGORIES.get(note["category"], CATEGORIES["system"])
        with st.container(key=f"note_{note['id']}"):
            render_html(
                f'<div class="dt-note {"is-unread" if not note["read"] else ""}">'
                f'<span class="dt-note-icon dt-tone-{tone}">{icon(sym)}</span><div class="dt-grow">'
                f'<div class="dt-note-meta">{badge(label, tone)}<span class="dt-muted">{note["date"]:%d.%m.%Y}</span>'
                f'{badge("Neu", "info") if not note["read"] else ""}</div>'
                f'<div class="dt-note-title">{esc(note["title"])}</div><p class="dt-muted">{esc(note["text"])}</p></div></div>'
            )
            st.button("Öffnen", key=f"notebtn_{note['id']}", icon=":material/arrow_forward:",
                      on_click=open_notification, args=(note["id"],))
