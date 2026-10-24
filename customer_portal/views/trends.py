"""
Trends & Analysen: regionale Heatmap, Entwicklung nach Risikokategorie, demografische
Trends und persönliche Risikoeinschätzung des Digital Twin.

Alle Werte stammen aus den synthetischen Dateien in generated_demodata/ und sind
ausdrücklich keine offiziellen oder geprüften Daten. Echte Datenquellen lassen sich
später über core/data.py anbinden, ohne diese Seite zu ändern.
"""
from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from core.data import (TODAY, home_coords, load_age_group_claims, load_disasters, load_incidents, place_coords,
                       place_options, place_profile, region_insights)
from core.state import navigate
from core.twin import load_forecast
from geo_heatmap import render_heatmap
from ui.components import badge, empty_state, esc, euro, icon, page_header, render_html

# Feste Farbe je Risikokategorie (Farbe folgt der Kategorie, nicht dem Rang). Geprüfte Reihenfolge.
GROUP_COLORS = {
    "Einbruch & Diebstahl": "#2a78d6",
    "Feuer & Elektro": "#eb6834",
    "Leitungswasser": "#1baf7a",
    "Vandalismus & Glas": "#eda100",
    "Cyber & Betrug": "#e87ba4",
}
PERIODS = {"Letzte 3 Monate": 3, "Letzte 6 Monate": 6, "Letzte 12 Monate": 12, "Letzte 24 Monate": 24}
# Kennzahlen aus forecast.py, die für Kundinnen und Kunden relevant sind (Schlüssel -> Anzeigename).
FORECAST_METRICS = {"einbrueche": "Einbruch & Diebstahl", "feueralarme": "Feuer & Elektro", "wasserschaeden": "Leitungswasser"}
AXIS = {"labelColor": "#475569", "titleColor": "#475569", "gridColor": "#E2E8F0", "domainColor": "#CBD5E1",
        "labelFont": "Inter", "titleFont": "Inter"}


# Baut die Analyseseite auf.
def render(ctx: dict) -> None:
    """Rendert Filter, Kennzahlen, Heatmap und Trenddiagramme."""
    page_header("Trends & Analysen", "Risiken in Ihrer Region und für Ihren Haushalt – verständlich aufbereitet.", "insights")
    render_html(
        f'<div class="dt-callout dt-callout-warn">{icon("science", "ms-sm")}<span><b>Beispieldaten:</b> Alle Werte stammen '
        f"aus synthetischen Testdaten des Projekts. Es handelt sich nicht um offizielle oder geprüfte Allianz-Daten.</span></div>"
    )
    _my_region(ctx["profile"])

    with st.spinner("Analysedaten werden geladen …"):
        incidents, disasters = load_incidents(), load_disasters()
    if incidents.empty:
        empty_state("Keine Analysedaten gefunden", "Die Datei generated_demodata/incidents.csv fehlt.", "database")
        return

    # Filterzeile über allen Diagrammen.
    regions = ["Deutschland gesamt"] + sorted(incidents["region"].unique())
    home_state = st.session_state.profile.get("federal_state", "")
    home_region = home_state if home_state in regions else regions[0]
    f1, f2, f3 = st.columns([1, 1, 2])
    region = f1.selectbox("Region", regions, index=regions.index(home_region), key="trf_region")
    period = f2.selectbox("Zeitraum", list(PERIODS), index=2, key="trf_period")
    groups = f3.multiselect("Risikokategorien", list(GROUP_COLORS), default=list(GROUP_COLORS), key="trf_groups",
                            placeholder="Kategorien wählen")

    months = PERIODS[period]
    start = pd.Timestamp(TODAY) - pd.DateOffset(months=months)
    data = incidents[(incidents["incident_date"] >= start) & incidents["group"].isin(groups)]
    if region != "Deutschland gesamt":
        data = data[data["region"] == region]
    nature = disasters[disasters["country"] == "DE"] if not disasters.empty else disasters
    if region != "Deutschland gesamt" and not nature.empty:
        nature = nature[nature["region"] == region]

    _kpis(data, nature, start)
    if data.empty:
        empty_state("Keine Vorfälle für diese Auswahl", "Erweitern Sie Zeitraum, Region oder Kategorien.", "filter_alt_off")
    else:
        map_col, chart_col = st.columns([1.15, 1], gap="medium")
        with map_col, st.container(key="tr_map"):
            _heatmap(data, nature, region)
        with chart_col, st.container(key="tr_trend"):
            _trend_chart(data, groups, months)

    with st.container(key="tr_forecast"):
        _forecast_section(region, home_state)

    demo_col, twin_col = st.columns(2, gap="medium")
    with demo_col, st.container(key="tr_demo"):
        _demographics()
    with twin_col, st.container(key="tr_twin"):
        _personal_risk(ctx)


# „Meine Region“: verständliche Aussagen über die Umgebung des Kunden, aus den Kundendaten abgeleitet.
def _my_region(profile: dict) -> None:
    """Zeigt Karten wie „Ihre Gegend ist sicher“ oder „Viele Menschen in Ihrem Alter“."""
    r = region_insights(profile)
    source = (f"Demo-Regionsprofil für {esc(r['label'].split(' (')[0])} plus {r['n']} anonymisierte Kundenprofile und regionale Vorfalldaten"
              if "Demo-Regionsprofil" in r["label"]
              else f"Abgeleitet aus {r['n']} anonymisierten Kundenprofilen in Ihrer Umgebung und den regionalen Vorfalldaten")
    heading = r["label"].replace(" (Demo-Regionsprofil)", "")
    render_html(f'<h3 class="dt-h3">Meine Region: {esc(heading)}</h3><p class="dt-tiny">{source}.</p>')
    cards = []

    # 1. Sicherheit
    if r["crime_all"] > 0:
        diff = (r["crime_region"] - r["crime_all"]) / r["crime_all"]
        if diff <= -0.15:
            head, tone = "Ihre Gegend ist sicher", "ok"
            text = f"Einbrüche und Diebstähle liegen hier {abs(diff):.0%} unter dem Bundesdurchschnitt."
        elif diff >= 0.15:
            head, tone = "Hier lohnt sich Einbruchschutz", "warn"
            text = f"Einbrüche und Diebstähle liegen hier {diff:.0%} über dem Bundesdurchschnitt."
        else:
            head, tone = "Durchschnittlich sichere Gegend", "info"
            text = "Einbrüche und Diebstähle liegen im Bundesdurchschnitt."
        if r["crime_trend"] and r["label"] == r["state"]:     # Trend gibt es nur je Bundesland
            text += f" Trend: {r['crime_trend']}."
        cards.append(("shield", head, text, tone, min(r["crime_region"] / max(r["crime_all"] * 2, 0.01), 1.0), "Vorfälle je 100 Kunden, relativ zum Bundesdurchschnitt"))

    # 2. Singles
    if r["singles"] >= 0.3:
        head = "Viele Singles in Ihrer Nähe"
    elif r["singles"] >= r["singles_all"]:
        head = "Etwas mehr Singles als im Schnitt"
    else:
        head = "Eher Paare und Familien"
    cards.append(("favorite", head, f"{r['singles']:.0%} der Menschen in Ihrer Region sind ledig, geschieden oder verwitwet "
                  f"(Deutschland: {r['singles_all']:.0%}).", "info", r["singles"], "Anteil Singles"))

    # 3. Altersgruppe
    head = "Viele Menschen in Ihrem Alter" if r["same_age"] >= max(0.25, r["same_age_all"]) else "Gemischte Altersstruktur"
    cards.append(("groups", head, f"{r['same_age']:.0%} sind wie Sie zwischen {r['my_age'].replace('-', ' und ')} Jahre alt "
                  f"(Deutschland: {r['same_age_all']:.0%}).", "info", r["same_age"], f"Anteil Altersgruppe {r['my_age']}"))

    # 4. Interessen
    if r["top_interests"]:
        cards.append(("interests", "Das bewegt Ihre Nachbarschaft", "Häufigste Interessen: " + ", ".join(r["top_interests"]) + ".",
                      "info", None, ""))

    # 5. Naturgefahren
    if r["nearby_disasters"]:
        n_ev = r["nearby_disasters"]
        cards.append(("flood", "Naturereignis in Ihrer Nähe",
                      f"{n_ev} aktive{'s' if n_ev == 1 else ''} oder erwartete{'s' if n_ev == 1 else ''} Ereignis{'' if n_ev == 1 else 'se'} in {r['state']}. "
                      "Details auf der Karte unten.", "warn", None, ""))
    else:
        cards.append(("sunny", "Aktuell keine Unwetterwarnung", f"In {r['state'] or 'Ihrer Region'} ist derzeit kein Naturereignis gemeldet.",
                      "ok", None, ""))

    cols = st.columns(2, gap="medium")
    for i, (ic, head, text, tone, value, caption) in enumerate(cards):
        with cols[i % 2], st.container(border=True):
            render_html(f'<div class="dt-card-head"><div><h4 class="dt-h4" style="margin:0">{icon(ic, "ms-sm")} {esc(head)}</h4></div>{badge({"ok": "Gut", "warn": "Beachten", "info": "Info"}[tone], tone)}</div>'
                        f'<p style="margin:6px 0 2px">{esc(text)}</p>')
            if value is not None:
                st.progress(float(max(0.0, min(value, 1.0))), text=caption)
    _place_check(profile, r)
    st.divider()


# Umzugs-Check: einen anderen Ort auswählen und mit dem Wohnort vergleichen.
def _place_check(profile: dict, home: dict) -> None:
    """Ortssuche mit Vergleich Wohnort vs. Zielort; Karte springt zum Ziel, Umzug kann direkt gemeldet werden."""
    render_html('<h4 class="dt-h4" style="margin-top:14px">Anderen Ort prüfen</h4>'
                '<p class="dt-tiny">Sie überlegen umzuziehen? Wählen Sie einen Ort und vergleichen Sie Sicherheit und Umfeld mit Ihrem Wohnort.</p>')
    options = [c for c in place_options() if c != profile["city"]]
    target = st.selectbox("Ort suchen", options, index=None, placeholder="Stadt eingeben, z. B. München", key="trf_place")
    st.session_state["trf_focus"] = None
    if not target:
        return
    there_profile = place_profile(target, profile)
    there = region_insights(there_profile)
    st.session_state["trf_focus"] = place_coords(target, there_profile)

    def pct(v):
        return f"{v:.0%}"

    crime_home = home["crime_region"] / max(home["crime_all"], 0.01)
    crime_there = there["crime_region"] / max(there["crime_all"], 0.01)
    rows = [
        ("Einbrüche vs. Bundesschnitt", f"{crime_home - 1:+.0%}", f"{crime_there - 1:+.0%}", "ok" if crime_there <= crime_home else "warn"),
        ("Singles", pct(home["singles"]), pct(there["singles"]), "info"),
        (f"In Ihrem Alter ({home['my_age']})", pct(home["same_age"]), pct(there["same_age"]), "info"),
        ("Naturereignisse aktiv/erwartet", str(home["nearby_disasters"]), str(there["nearby_disasters"]),
         "ok" if there["nearby_disasters"] <= home["nearby_disasters"] else "warn"),
        ("Typische Interessen", ", ".join(home["top_interests"]), ", ".join(there["top_interests"]), "info"),
    ]
    table = "".join(f"<tr><td>{esc(k)}</td><td>{esc(a)}</td><td><b>{esc(b)}</b></td></tr>" for k, a, b, _ in rows)
    render_html(f'<table class="dt-table" style="width:100%"><thead><tr><th></th><th>{esc(profile["city"])} (heute)</th>'
                f'<th>{esc(target)}</th></tr></thead><tbody>{table}</tbody></table>')

    verdict = []
    verdict.append("sicherer als Ihr Wohnort" if crime_there < crime_home * 0.9 else
                   "weniger sicher als Ihr Wohnort" if crime_there > crime_home * 1.1 else "ähnlich sicher wie Ihr Wohnort")
    if there["singles"] >= 0.45:
        verdict.append("viele Singles")
    if there["same_age"] >= 0.3:
        verdict.append("viele Menschen in Ihrem Alter")
    if there["nearby_disasters"] > home["nearby_disasters"]:
        verdict.append("mehr Unwetterwarnungen, Elementarschutz prüfen")
    render_html(f'<div class="dt-callout">{icon("insights", "ms-sm")}<span><b>{esc(target)}:</b> {esc(", ".join(verdict))}. '
                f'Quelle: {"Demo-Regionsprofil" if "Demo" in there["label"] else str(there["n"]) + " Kundenprofile"} und regionale Vorfalldaten.</span></div>')
    st.button(f"Umzug nach {target} melden", key="trf_move", icon=":material/moving:", type="primary",
              on_click=_prefill_move, args=(there_profile,))


def _prefill_move(there_profile: dict) -> None:
    """Öffnet das Ereignisformular im Profil mit dem gewählten Ort vorausgefüllt."""
    st.session_state.update(event_form_open=True, ev_type="umzug", ev_postal=there_profile["postal_code"],
                            ev_city=there_profile["city"], ev_state=there_profile.get("federal_state", ""))
    navigate("profile")


# Vier Kennzahlen mit Tooltips zur Erklärung.
def _kpis(data: pd.DataFrame, nature: pd.DataFrame, start: pd.Timestamp) -> None:
    """Zeigt Kennzahlen zur aktuellen Filterauswahl."""
    near = 0
    if not data.empty:
        near = int((data["postal_code"].str[:2] == st.session_state.profile["postal_code"][:2]).sum())
    upcoming = int(nature["status"].isin(["active", "forecast"]).sum()) if not nature.empty else 0
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Vorfälle", len(data), help="Anzahl der Schadenereignisse im gewählten Zeitraum, Gebiet und in den gewählten Kategorien.")
    c2.metric("Ø Schadenhöhe", euro(data["damage_eur"].mean(), 0) if not data.empty else "–",
              help="Durchschnittlicher Schaden je Vorfall. Einzelne Großschäden (z. B. Brände) heben den Wert stark an.")
    c3.metric("In Ihrer PLZ-Region", near, help="Vorfälle mit denselben ersten zwei Ziffern Ihrer Postleitzahl.")
    c4.metric("Naturereignisse aktiv/erwartet", upcoming,
              help="Aktuelle oder vorhergesagte Ereignisse wie Starkregen oder Hochwasser in der gewählten Region.")


# Regionale Heatmap: Dichte der Vorfälle, Naturereignisse und Ihr Wohnort.
def _heatmap(data: pd.DataFrame, nature: pd.DataFrame, region: str) -> None:
    """Zeigt eine interaktive Karte mit Heatmap und Markern."""
    render_html('<h3 class="dt-h3">Regionale Risiko-Heatmap</h3>')
    points = data.assign(weight=data["severity_level"].astype(float), tip=data["label"] + " · " + data["city"])
    focus = st.session_state.get("trf_focus")
    center = focus or ((data["latitude"].mean(), data["longitude"].mean()) if region != "Deutschland gesamt" else (51.1, 10.4))
    zoom = 8 if focus else 6 if region != "Deutschland gesamt" else 4.8
    render_heatmap(points, nature, home=_home(), center=center, zoom=zoom, height=380)
    render_html(
        '<div class="dt-legend"><span><i class="dt-sw dt-sw-heat"></i>Dichte der Vorfälle (gewichtet nach Schwere)</span>'
        '<span><i class="dt-sw dt-sw-home"></i>Ihr Wohnort</span>'
        '<span><i class="dt-sw dt-sw-alert"></i>Naturereignis aktiv/erwartet</span>'
        '<span><i class="dt-sw dt-sw-past"></i>Naturereignis vergangen</span></div>'
    )


# Prognose: beobachtete Monatswerte, Trend-Vorhersage und Unsicherheitsband aus forecast.py.
def _forecast_section(region: str, home_state: str) -> None:
    """Zeigt die Entwicklung einer Risikokennzahl in der Region und die Prognose für die nächsten Monate."""
    # Bei "Deutschland gesamt" zeigt die Prognose das Bundesland des Kunden (Zeitreihen gibt es nur je Bundesland).
    target = region if region != "Deutschland gesamt" else home_state
    render_html(f'<h3 class="dt-h3">Prognose für {esc(target)}</h3>'
                '<p class="dt-tiny">Beobachtete Monatswerte und Trend-Vorhersage (lineare Regression mit Saisonalität). '
                'Modellschätzung, keine Garantie.</p>')
    c1, c2 = st.columns([1, 1])
    metric_label = c1.selectbox("Kennzahl", list(FORECAST_METRICS.values()), key="trf_metric")
    metric = next(k for k, v in FORECAST_METRICS.items() if v == metric_label)
    steps = c2.slider("Monate in die Zukunft", 3, 12, 6, key="trf_steps")
    result = load_forecast(target, metric, steps)
    if not result:
        empty_state("Keine Prognose verfügbar", f"Für {target} liegen keine regionalen Zeitreihen vor.", "trending_flat")
        return

    hist = pd.DataFrame(result["history"]).tail(18).assign(Art="Beobachtet")
    fc = pd.DataFrame(result["forecast"]).assign(Art="Prognose")
    bridge = hist.tail(1).assign(Art="Prognose")                       # verbindet die Linien
    lines = pd.concat([hist, bridge, fc]).rename(columns={"month": "Monat", "value": "Wert"})
    band = fc.rename(columns={"month": "Monat"})
    domain = list(lines["Monat"].unique())
    base_x = alt.X("Monat:O", title=None, sort=domain, axis=alt.Axis(labelAngle=-45))
    area = alt.Chart(band).mark_area(color="#2a78d6", opacity=0.15).encode(x=base_x, y="lo:Q", y2="hi:Q")
    line = alt.Chart(lines).mark_line(point=True).encode(
        x=base_x, y=alt.Y("Wert:Q", title="Vorfälle pro Monat"),
        color=alt.Color("Art:N", scale=alt.Scale(domain=["Beobachtet", "Prognose"], range=["#334155", "#2a78d6"]),
                        legend=alt.Legend(orient="bottom", title=None, labelFont="Inter")),
        strokeDash=alt.condition(alt.datum.Art == "Prognose", alt.value([6, 4]), alt.value([1, 0])),
        tooltip=["Monat:O", alt.Tooltip("Wert:Q", format=".1f"), "Art:N"],
    )
    chart = (area + line).properties(height=280).configure_axis(**AXIS).configure_view(strokeWidth=0).configure(background="#FFFFFF")
    st.altair_chart(chart, use_container_width=True)
    last, end = fc.iloc[0], fc.iloc[-1]
    render_html(f'<p class="dt-tiny"><b>Trend:</b> {esc(result["trend"])} · In {steps} Monaten erwartet: '
                f'{end["value"]:.1f} (Band {end["lo"]:.1f} bis {end["hi"]:.1f}) · Nächster Monat: {last["value"]:.1f}</p>')


# Gestapelte Balken: Vorfälle je Monat bzw. Quartal und Kategorie.
def _trend_chart(data: pd.DataFrame, groups: list[str], months: int) -> None:
    """Zeigt die zeitliche Entwicklung der Vorfälle je Risikokategorie."""
    freq_label = "Monat" if months <= 6 else "Quartal"
    render_html(f'<h3 class="dt-h3">Entwicklung nach Kategorie</h3><p class="dt-tiny">Vorfälle pro {freq_label}</p>')
    period = data["incident_date"].dt.to_period("M" if months <= 6 else "Q")
    counts = data.assign(period=period.astype(str)).groupby(["period", "group"]).size().reset_index(name="Vorfälle")
    counts = counts.rename(columns={"period": freq_label, "group": "Kategorie"})
    domain = [g for g in GROUP_COLORS if g in groups]
    chart = (
        alt.Chart(counts)
        .mark_bar(stroke="#ffffff", strokeWidth=2)
        .encode(
            x=alt.X(f"{freq_label}:O", title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("Vorfälle:Q", title="Vorfälle", axis=alt.Axis(tickMinStep=1)),
            color=alt.Color("Kategorie:N", scale=alt.Scale(domain=domain, range=[GROUP_COLORS[g] for g in domain]),
                            legend=alt.Legend(orient="bottom", columns=2, title=None, labelFont="Inter")),
            order=alt.Order("Kategorie:N"),
            tooltip=[f"{freq_label}:O", "Kategorie:N", "Vorfälle:Q"],
        )
        .properties(height=300)
        .configure_axis(**AXIS)
        .configure_view(strokeWidth=0)
        .configure(background="#FFFFFF")
    )
    st.altair_chart(chart, use_container_width=True)
    with st.expander("Daten als Tabelle", icon=":material/table:"):
        st.dataframe(counts, hide_index=True)


# Demografische Trends: Fälle je Altersgruppe (Sach- und Gesundheitsfälle).
def _demographics() -> None:
    """Zeigt Sach- und Gesundheitsfälle je Altersgruppe der Kundinnen und Kunden."""
    render_html('<h3 class="dt-h3">Demografische Trends</h3><p class="dt-tiny">Gemeldete Fälle je Altersgruppe (alle Demokunden)</p>')
    claims = load_age_group_claims()
    if claims.empty:
        empty_state("Keine demografischen Daten", "Kunden- oder Falldaten fehlen.", "groups")
        return
    claims = claims.rename(columns={"age_group": "Altersgruppe", "kind": "Art", "count": "Fälle"})
    chart = (
        alt.Chart(claims)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("Altersgruppe:O", title=None, axis=alt.Axis(labelAngle=0)),
            xOffset="Art:N",
            y=alt.Y("Fälle:Q", axis=alt.Axis(tickMinStep=1)),
            color=alt.Color("Art:N", scale=alt.Scale(domain=["Sachschäden", "Gesundheitsfälle"], range=["#2a78d6", "#eb6834"]),
                            legend=alt.Legend(orient="bottom", title=None, labelFont="Inter")),
            tooltip=["Altersgruppe:O", "Art:N", "Fälle:Q"],
        )
        .properties(height=260)
        .configure_axis(**AXIS)
        .configure_view(strokeWidth=0)
        .configure(background="#FFFFFF")
    )
    st.altair_chart(chart, use_container_width=True)


# Persönliche Risiken laut Digital Twin, mit Treibern als Erklärung.
def _personal_risk(ctx: dict) -> None:
    """Zeigt die Risikoeinschätzung und Lebensereignis-Prognosen des Digital Twin."""
    render_html('<h3 class="dt-h3">Ihr persönliches Risikoprofil</h3>'
                '<p class="dt-tiny">Modellschätzung des Digital Twin für die nächsten 12 Monate – keine bestätigte Tatsache.</p>')
    twin = ctx["twin"]
    if not twin:
        empty_state("Digital Twin nicht verfügbar", "Die persönliche Einschätzung kann gerade nicht berechnet werden.", "cloud_off")
        return
    risks = pd.DataFrame(
        [{"Risiko": label, "Wahrscheinlichkeit": p, "Treiber": ", ".join(d) or "keine besonderen"} for _, label, p, _, d in twin.risks]
    )
    bars = alt.Chart(risks).encode(
        y=alt.Y("Risiko:N", sort="-x", title=None),
        x=alt.X("Wahrscheinlichkeit:Q", axis=alt.Axis(format="%", title=None)),
        tooltip=["Risiko:N", alt.Tooltip("Wahrscheinlichkeit:Q", format=".1%"), "Treiber:N"],
    )
    chart = (
        (bars.mark_bar(color="#2a78d6", cornerRadiusTopRight=4, cornerRadiusBottomRight=4, height=18)
         + bars.mark_text(align="left", dx=6, color="#334155", font="Inter").encode(text=alt.Text("Wahrscheinlichkeit:Q", format=".1%")))
        .properties(height=150)
        .configure_axis(**AXIS)
        .configure_view(strokeWidth=0)
        .configure(background="#FFFFFF")
    )
    st.altair_chart(chart, use_container_width=True)
    events = "".join(f"<li><span>{esc(label)}</span><b>{p:.0%}</b></li>" for _, label, p in twin.events)
    render_html(f'<h4 class="dt-h4">Wahrscheinliche Lebensereignisse</h4><ul class="dt-kv">{events}</ul>')


def _home() -> tuple[float, float]:
    """Koordinaten des Wohnorts des angemeldeten Kunden."""
    profile = st.session_state.profile
    return home_coords(profile["postal_code"], profile.get("federal_state", ""))
