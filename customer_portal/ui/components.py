"""
Wiederverwendbare UI-Bausteine (Designsystem).

Alle Seiten bauen ihre Oberfläche aus diesen Funktionen, damit Karten, Badges,
Kennzahlen und Symbole überall gleich aussehen. Farben stehen in styles/portal.css.
"""
from __future__ import annotations

import html

import streamlit as st

# Gibt HTML ohne Markdown-Nebenwirkungen aus (Einrückungen würden sonst zu Codeblöcken).
def render_html(markup: str) -> None:
    """Rendert ein HTML-Fragment über st.markdown."""
    st.markdown("".join(line.strip() for line in markup.splitlines()), unsafe_allow_html=True)


# Maskiert Text für die Ausgabe in HTML.
def esc(text: object) -> str:
    """Wandelt Sonderzeichen in HTML-Entitäten um."""
    return html.escape(str(text))


# Material-Symbol als Inline-Element; dekorativ, die Bedeutung steht immer zusätzlich als Text daneben.
def icon(name: str, css_class: str = "") -> str:
    """Gibt das HTML für ein Material-Symbol zurück."""
    return f'<span class="ms {css_class}" aria-hidden="true">{name}</span>'


# Wortmarke des Portals. Hier kann später ein freigegebenes Original-Logo eingesetzt werden.
def logo_html(compact: bool = False) -> str:
    """Gibt die Wort-Bild-Marke „Digital Twin“ zurück (kein offizielles Allianz-Logo)."""
    mark = (
        '<svg class="dt-logo-mark" viewBox="0 0 40 40" aria-hidden="true">'
        '<rect width="40" height="40" rx="11" fill="#003781"/>'
        '<circle cx="16" cy="20" r="8.5" fill="none" stroke="#fff" stroke-width="3"/>'
        '<circle cx="24" cy="20" r="8.5" fill="none" stroke="#7FC4FD" stroke-width="3"/></svg>'
    )
    sub = "" if compact else '<span class="dt-logo-sub">Kundenportal · Prototyp</span>'
    return (
        f'<div class="dt-logo">{mark}<div><span class="dt-logo-word">Allianz <b>Digital Twin</b></span>{sub}</div></div>'
    )


# Hinweisleiste, dass alle Inhalte fiktiv sind. Erscheint auf jeder Seite.
def prototype_notice() -> None:
    """Zeigt den Prototyp-Hinweis über dem Seiteninhalt."""
    render_html(
        f'<div class="dt-proto">{icon("science")}<span><b>Prototyp</b> · Alle Kunden-, Vertrags- und Risikodaten sind '
        f"fiktiv und keine echten Versicherungsinformationen.</span></div>"
    )


# Seitenkopf mit Titel, Untertitel und optionalem Symbol.
def page_header(title: str, subtitle: str = "", icon_name: str = "") -> None:
    """Rendert den Kopf einer Portalseite."""
    sym = f'<span class="dt-page-icon">{icon(icon_name)}</span>' if icon_name else ""
    sub = f'<p class="dt-page-sub">{esc(subtitle)}</p>' if subtitle else ""
    render_html(f'<div class="dt-page-head">{sym}<div><h1 class="dt-h1">{esc(title)}</h1>{sub}</div></div>')


# Abschnittsüberschrift innerhalb einer Karte oder Seite.
def section_title(title: str, hint: str = "") -> None:
    """Rendert eine Zwischenüberschrift mit optionalem Hinweis rechts."""
    side = f'<span class="dt-section-hint">{esc(hint)}</span>' if hint else ""
    render_html(f'<div class="dt-section"><h2 class="dt-h2">{esc(title)}</h2>{side}</div>')


# Status-Badge mit Symbol und Text (nie nur Farbe). tone: ok, warn, info, danger, neutral.
def badge(label: str, tone: str = "neutral", icon_name: str = "") -> str:
    """Gibt das HTML eines Status-Badges zurück."""
    sym = icon(icon_name, "ms-sm") if icon_name else ""
    return f'<span class="dt-badge dt-badge-{tone}">{sym}{esc(label)}</span>'


# Kennzahl-Kachel mit Wert, Beschriftung und optionaler Erläuterung.
def stat_tile(label: str, value: str, icon_name: str, note: str = "", tone: str = "info") -> str:
    """Gibt das HTML einer Kennzahl-Kachel zurück."""
    note_html = f'<div class="dt-stat-note">{esc(note)}</div>' if note else ""
    return (
        f'<div class="dt-stat dt-tone-{tone}"><span class="dt-stat-icon">{icon(icon_name)}</span>'
        f'<div><div class="dt-stat-label">{esc(label)}</div><div class="dt-stat-value">{esc(value)}</div>{note_html}</div></div>'
    )


# Ring-Anzeige für den Absicherungsgrad (SVG, skaliert mit der Karte).
def coverage_ring(percent: int, caption: str) -> str:
    """Gibt einen Fortschrittsring mit Prozentwert in der Mitte zurück."""
    radius, stroke = 52, 12
    circumference = 2 * 3.14159 * radius
    filled = circumference * percent / 100
    tone = "ok" if percent >= 80 else "warn" if percent >= 55 else "danger"
    return (
        f'<div class="dt-ring dt-ring-{tone}" role="img" aria-label="Absicherungsgrad {percent} Prozent">'
        f'<svg viewBox="0 0 128 128"><circle cx="64" cy="64" r="{radius}" class="dt-ring-track" stroke-width="{stroke}" fill="none"/>'
        f'<circle cx="64" cy="64" r="{radius}" class="dt-ring-value" stroke-width="{stroke}" fill="none" '
        f'stroke-linecap="round" stroke-dasharray="{filled:.1f} {circumference:.1f}" transform="rotate(-90 64 64)"/></svg>'
        f'<div class="dt-ring-label"><span class="dt-ring-pct">{percent}&nbsp;%</span>'
        f'<span class="dt-ring-cap">{esc(caption)}</span></div></div>'
    )


# Leerer Zustand mit Symbol, Text und optionalem Hinweis.
def empty_state(title: str, text: str, icon_name: str = "inbox") -> None:
    """Zeigt einen freundlichen Leerzustand an."""
    render_html(
        f'<div class="dt-empty">{icon(icon_name, "ms-xl")}<div class="dt-empty-title">{esc(title)}</div>'
        f'<div class="dt-empty-text">{esc(text)}</div></div>'
    )


# Formatiert Beträge im deutschen Format, z. B. 1.234,50 €.
def euro(value: float, decimals: int = 2) -> str:
    """Gibt einen Eurobetrag im deutschen Zahlenformat zurück."""
    text = f"{value:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{text} €"
