"""
Gemeinsame UI-Hilfsfunktionen: HTML-Ausgabe, Symbole und kleine Bausteine.

Alle anderen Komponenten nutzen diese Funktionen, damit Symbole, Escaping
und Statusanzeigen an einer einzigen Stelle definiert sind.
"""
from __future__ import annotations

import html

import streamlit as st

from data.mock_data import CATEGORIES, COVERAGE_STATUS
from i18n import t, tr


# Pfaddaten der Inline-SVG-Symbole (24×24, Linienstil). So werden keine
# Bilddateien oder externen Icon-Bibliotheken benötigt.
_ICON_PATHS: dict[str, str] = {
    "home": '<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/><path d="M10 21v-6h4v6"/>',
    "house": '<path d="M3 11 12 4l9 7"/><path d="M5 10v10h14V10"/><rect x="10" y="14" width="4" height="6"/>',
    "users": '<circle cx="9" cy="8" r="4"/><path d="M2 21v-1a6 6 0 0 1 6-6h2a6 6 0 0 1 6 6v1"/>'
             '<path d="M16 3.5a4 4 0 0 1 0 7.5"/><path d="M22 21v-1a6 6 0 0 0-4-5.6"/>',
    "tasks": '<rect x="3" y="3" width="18" height="18" rx="3"/><path d="m8 12 3 3 5-6"/>',
    "bell": '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>',
    "user": '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
    "chevron_right": '<path d="m9 18 6-6-6-6"/>',
    "chevron_down": '<path d="m6 9 6 6 6-6"/>',
    "umbrella": '<path d="M22 12a10 10 0 0 0-20 0Z"/><path d="M12 12v7a2 2 0 0 0 4 0"/><path d="M12 2v0"/>'
                '<path d="M5 2 4 4"/><path d="M19 2l1 2"/>',
    "bike": '<circle cx="5.5" cy="17.5" r="3.5"/><circle cx="18.5" cy="17.5" r="3.5"/>'
            '<circle cx="15" cy="5" r="1"/><path d="M12 17.5V14l-3-3 4-3 2 3h2"/>',
    "map_pin": '<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/>',
    "help": '<circle cx="12" cy="12" r="10"/><path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3"/><path d="M12 17h.01"/>',
    "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/><path d="m9 12 2 2 4-4"/>',
    "waves": '<path d="M2 7c1.5 1.3 3 1.3 4.5 0s3-1.3 4.5 0 3 1.3 4.5 0 3-1.3 4.5 0"/>'
             '<path d="M2 12c1.5 1.3 3 1.3 4.5 0s3-1.3 4.5 0 3 1.3 4.5 0 3-1.3 4.5 0"/>'
             '<path d="M2 17c1.5 1.3 3 1.3 4.5 0s3-1.3 4.5 0 3 1.3 4.5 0 3-1.3 4.5 0"/>',
    "building": '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M9 7h1M14 7h1M9 11h1M14 11h1"/>'
                '<path d="M10 21v-4h4v4"/>',
    "heart": '<path d="M19 14c1.5-1.5 3-3.2 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.8 0-3 .5-4.5 2-1.5-1.5-2.7-2-4.5-2'
             'A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4 3 5.5l7 7Z"/>',
    "calendar": '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
    "message": '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2Z"/>',
    "file": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6"/>'
            '<path d="M16 13H8M16 17H8M10 9H8"/>',
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "alert": '<path d="M12 7v6"/><path d="M12 17h.01"/>',
    "minus": '<path d="M6 12h12"/>',
    "info": '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
    "cloud_rain": '<path d="M20 16.6A5 5 0 0 0 18 7h-1.3A8 8 0 1 0 4 15.3"/><path d="M8 14v4M12 16v5M16 14v4"/>',
    "warning": '<path d="m21.7 18-8-14a2 2 0 0 0-3.4 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.7-3Z"/>'
               '<path d="M12 9v4"/><path d="M12 17h.01"/>',
    "external": '<path d="M15 3h6v6"/><path d="M10 14 21 3"/>'
                '<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>',
    "target":'<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
}


# Erzeugt ein Inline-SVG-Symbol. Symbole sind rein dekorativ (aria-hidden),
# die Bedeutung wird immer zusätzlich als Text angezeigt.
def icon(name: str, css_class: str = "c360-icon") -> str:
    """Gibt das SVG-Markup für das angegebene Symbol zurück."""
    paths = _ICON_PATHS.get(name, _ICON_PATHS["info"])
    return (
        f'<svg class="{css_class}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{paths}</svg>'
    )


# Übersetzt Texte aus den Daten in die aktive Sprache und maskiert sie, bevor sie
# in HTML eingesetzt werden. So sind alle Datentexte automatisch zweisprachig.
def esc(text: str) -> str:
    """Übersetzt den Text (siehe i18n.tr) und wandelt Sonderzeichen in HTML-Entitäten um."""
    return html.escape(tr(str(text)))


# Gibt HTML über st.markdown aus. Zeilenumbrüche und Einrückungen werden entfernt,
# damit der Markdown-Parser von Streamlit keine Codeblöcke daraus macht.
def render_html(markup: str) -> None:
    """Rendert ein HTML-Fragment ohne Markdown-Nebenwirkungen."""
    compact = "".join(line.strip() for line in markup.splitlines())
    st.markdown(compact, unsafe_allow_html=True)


# Liefert die CSS-Klasse einer Kategorie; daran hängen Farben für Rand, Badge und Symbol.
# Unbekannte Schlüssel (z. B. "neutral" für Verträge ohne Handlungsbedarf) erhalten Blau.
def category_class(category_key: str) -> str:
    """Gibt die CSS-Klasse für die fachliche Kategorie zurück (z. B. c360-cat-prevention)."""
    return f"c360-cat-{category_key if category_key in CATEGORIES else 'neutral'}"


# Baut die Statusanzeige einer Versicherung aus Symbol und Text,
# damit der Status nicht nur über die Farbe erkennbar ist.
def status_badge(status_key: str) -> str:
    """Gibt das HTML der Statusanzeige (Symbol + Text) für eine Versicherung zurück."""
    status = COVERAGE_STATUS[status_key]
    return (
        f'<span class="c360-status c360-status-{status.key}">'
        f'<span class="c360-status-dot">{icon(status.symbol, "c360-icon c360-icon-xs")}</span>'
        f"{esc(status.label)}</span>"
    )


# Wandelt eine Liste in eine HTML-Liste um; leere Listen erhalten einen Hinweistext.
def html_list(items: list[str], empty_text: str | None = None, ordered: bool = False) -> str:
    """Gibt eine HTML-Aufzählung der Einträge oder einen Platzhaltertext zurück."""
    if not items:
        return f'<div class="c360-muted">{esc(empty_text or t("not_specified"))}</div>'
    tag = "ol" if ordered else "ul"
    rows = "".join(f"<li>{esc(item)}</li>" for item in items)
    return f'<{tag} class="c360-list">{rows}</{tag}>'
