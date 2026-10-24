"""
Bereitet die Digital Twins aller Kunden für die Oberfläche auf.

Kunden kommen über data_loader, alle Werte aus dem DigitalTwin. Diese Datei kennt keine
CSV-Dateien; eine andere Datenquelle betrifft nur den Loader. Erzeugt werden dieselben
Datenklassen wie in mock_data.py, damit die Oberfläche unverändert bleibt.
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

from data.mock_data import CATEGORIES, Coverage, Customer, Event, Reason, Signal

PROJECT_ROOT = Path(__file__).resolve().parents[2]
# Projektmodule (data_loader, digital_twin) liegen oberhalb von dashboard/.
sys.path.append(str(PROJECT_ROOT))
from dataclasses import asdict  # noqa: E402
from data_loader import display_name, load_all_customers, salutation  # noqa: E402
from digital_twin import DigitalTwin  # noqa: E402
from models import TODAY  # noqa: E402
from models import Customer as TwinCustomer  # noqa: E402

CONFIG_PATH = PROJECT_ROOT / "config.toml"
NOT_SPECIFIED = "Keine Angaben"

BUILDING_TYPES = {
    "apartment": "Wohnung",
    "semi_detached": "Doppelhaushälfte",
    "terraced_house": "Reihenhaus",
    "detached_house": "Einfamilienhaus",
}
FINANCES = {"low": "niedrig", "medium": "mittel", "high": "hoch"}
EVENT_LABELS = {
    "kind": ("Geburt eines Kindes", "heart"),
    "auto": ("Autokauf", "target"),
    "ebike": ("E-Bike-Kauf", "bike"),
    "umzug": ("Umzug", "house"),
}
URGENCY = {1: "Diese Woche", 2: "Diesen Monat", 3: "Bei Gelegenheit"}

# Produkte aus config.toml -> Versicherungssparte im Dashboard.
PRODUCT_COVERAGE = {
    "Familienhaftpflicht": "haftpflicht",
    "Kfz-Versicherung": "kfz",
    "Elementarbaustein": "elementar",
    "Rauchmelder prüfen": "hausrat",
    "Wassersensor anbieten": "hausrat",
    "Hausrat-Summe bald prüfen": "hausrat",
    "Umzugs-Check": "hausrat",
    "Einbruchschutz ansprechen": "hausrat",
}
PRODUCT_ICONS = {
    "Familienhaftpflicht": "heart",
    "Kfz-Versicherung": "target",
    "Elementarbaustein": "umbrella",
    "Rauchmelder prüfen": "warning",
    "Wassersensor anbieten": "waves",
    "Hausrat-Summe bald prüfen": "house",
    "Umzugs-Check": "house",
    "Einbruchschutz ansprechen": "shield",
}
# Sparte: (Bezeichnung, Symbol, Gefahren aus config.toml, Life Events aus config.toml)
COVERAGES = {
    "hausrat": ("Hausrat", "house", ["feuer", "leitungswasser"], ["umzug"]),
    "elementar": ("Elementar", "waves", ["hochwasser"], []),
    "haftpflicht": ("Haftpflicht", "shield", [], ["kind"]),
    "kfz": ("Kfz", "target", [], ["auto", "ebike"]),
}
HAZARD_ICONS = {"feuer": "warning", "hochwasser": "waves", "leitungswasser": "building"}
SOURCES = ["Kundendaten", "Gebäudedaten", "Life Events"]


def _signals(names, results, icons) -> list[Signal]:
    return [
        Signal(
            results[name].label,
            results[name].p_12m,
            list(results[name].drivers) or ["Basisrate ohne besondere Treiber"],
            icons.get(name, "info"),
        )
        for name in names
        if name in results
    ]


def _build_coverages(twin: DigitalTwin, recommendations, risks, events) -> list[Coverage]:
    coverages = []
    for key, (label, coverage_icon, hazards, life_events) in COVERAGES.items():
        recs = [r for r in recommendations if PRODUCT_COVERAGE.get(r.product) == key]
        if twin.has(key):
            status = "protected"
        elif recs:
            status = "check"
        else:
            status = "missing"

        signals = _signals(hazards, risks, HAZARD_ICONS) + _signals(
            life_events, events, {e: EVENT_LABELS.get(e, ("", "calendar"))[1] for e in life_events}
        )
        signals.sort(key=lambda s: s.probability, reverse=True)
        reasons = [
            Reason(
                s.icon,
                s.title,
                f"{s.probability:.0%} in den nächsten 12 Monaten",
                "Treiber: " + ", ".join(s.sources),
            )
            for s in signals
        ]
        reasons.append(Reason("file", "Vertragsdaten", "Keine Vertragsdaten vorhanden", show_contract=True))
        top = recs[0] if recs else None
        coverages.append(
            Coverage(
                key=key,
                label=label,
                icon=coverage_icon,
                status=status,
                contract={"Status": "Keine Vertragsdaten vorhanden"},
                recommendation=" ".join(r.reason + "." for r in recs) or "Kein Handlungsbedarf erkannt.",
                sources=SOURCES,
                signals=signals,
                reasons=reasons,
                action_title=f"{top.product} besprechen" if top else "",
                benefit=CATEGORIES[top.category].description if top else "",
                action_category=top.category if top else None,
                action_icon=PRODUCT_ICONS.get(top.product, coverage_icon) if top else "",
                consent="Nutzung der Kunden- und Gebäudedaten aus dem Digital Twin.",
            )
        )
    return coverages


def _build_customer(twin_customer: TwinCustomer) -> tuple[tuple, Customer]:
    twin = DigitalTwin(twin_customer, config_path=CONFIG_PATH)
    person, house = twin.person, twin.house
    customer_id = person.customer_id
    risks = twin.risks()
    events = twin.predicted_events()
    recommendations = sorted(
        twin.recommendations(), key=lambda r: (r.priority, CATEGORIES[r.category].order)
    )
    top = recommendations[0] if recommendations else None
    category = top.category if top else "cross_sell"
    rec_priority = top.priority if top else 3
    housing = BUILDING_TYPES.get(house.building_type, house.building_type)

    timeline = [
        Event(
            event.date.strftime("%d.%m.%Y"),
            EVENT_LABELS.get(event.type, (event.type, "calendar"))[0],
            EVENT_LABELS.get(event.type, (event.type, "calendar"))[1],
            is_new=(TODAY - event.date).days < 90,
        )
        for event in sorted(twin.customer.life_events, key=lambda e: e.date, reverse=True)
    ]
    explanation = [
        f"Kundendaten: Altersgruppe {person.age_group}, Beruf {person.occupation}, "
        f"finanzielle Situation {FINANCES.get(person.financial_situation, person.financial_situation)}, "
        f"Kunde seit {person.customer_since:%d.%m.%Y}.",
        f"Gebäudedaten: {housing}, Baujahr {house.year}, Risikozone {house.riskzone}, "
        f"{'mit' if house.basement else 'ohne'} Keller, {house.floors} Etagen.",
        *(f"{r.product}: {r.reason}." for r in recommendations),
    ]
    max_risk = max((r.p_12m for r in risks.values()), default=0)

    first, last = display_name(customer_id, person.gender)
    title = salutation(person.gender)
    customer = Customer(
        id=customer_id,
        name=f"{first} {last}",
        salutation=f"{title} {last}".strip(),
        age=person.age_group,
        city=person.city or NOT_SPECIFIED,
        housing=f"{housing}, Baujahr {house.year}",
        priority=0,
        category=category,
        urgency=URGENCY.get(rec_priority, URGENCY[3]),
        topic_icon=PRODUCT_ICONS.get(top.product, "info") if top else "info",
        reason=top.reason if top else "Keine Auffälligkeiten erkannt",
        headline=f"{URGENCY.get(rec_priority, URGENCY[3])} kontaktieren" if top else "Kein akuter Handlungsbedarf",
        situation=[r.reason + "." for r in recommendations[:2]] or ["Keine Auffälligkeiten erkannt."],
        recommendation=f"{top.product} besprechen." if top else "Beim nächsten Kontakt Situation bestätigen.",
        benefit=CATEGORIES[category].description,
        last_contact=NOT_SPECIFIED,
        sources=SOURCES,
        explanation=explanation,
        coverages=_build_coverages(twin, recommendations, risks, events),
        events=timeline,
        conversation_opening=(
            f"Guten Tag, ich melde mich, weil {top.reason[0].lower() + top.reason[1:]}."
            if top else "Guten Tag, ich möchte kurz prüfen, ob Ihre Absicherung noch zu Ihrer Situation passt."
        ),
        conversation_questions=[f"Darf ich Ihnen kurz erläutern, was {r.product} für Sie bedeutet?" for r in recommendations[:3]],
        conversation_goal=(
            f"Gemeinsam klären, ob {top.product} für {title + ' ' + last if title else first + ' ' + last} sinnvoll ist."
            if top else "Aktuelle Situation und Absicherung bestätigen."
        ),
        next_action=asdict(twin.next_best_action()),
    )
    # Reihenfolge: Empfehlungspriorität, dann frische Signale (Life Event in den letzten 30 Tagen),
    # dann Kategorie (Prävention vor Lücke vor Cross-Sell), dann höchstes Risiko.
    fresh_event = any((TODAY - e.date).days <= 30 for e in twin.customer.life_events)
    sort_key = (rec_priority, 0 if fresh_event else 1, CATEGORIES[category].order, -max_risk)
    return sort_key, customer


def _data_stamp() -> float:
    folder = PROJECT_ROOT / "generated_demodata"
    return max((f.stat().st_mtime for f in folder.glob("*.csv")), default=0.0)


# Neu berechnet nur, wenn sich eine CSV ändert (vorher alle 10 s, bei 250 Kunden spürbar).
@st.cache_data(show_spinner="Kunden werden aus ihren Digital Twins geladen …")
def _customers(stamp: float) -> list[Customer]:
    ranked = sorted(
        (_build_customer(twin_customer) for twin_customer in load_all_customers().values()),
        key=lambda item: item[0],
    )
    customers = [customer for _, customer in ranked]
    for rank, customer in enumerate(customers, start=1):
        customer.priority = rank
    return customers


def get_customers() -> list[Customer]:
    """Alle Kunden aus ihren Digital Twins, sortiert nach Kategorie, Empfehlungspriorität und höchstem Risiko."""
    return _customers(_data_stamp())


def get_customer(customer_id: str) -> Customer | None:
    """Kunde anhand seiner ID oder None, falls unbekannt."""
    return next((c for c in get_customers() if c.id == customer_id), None)
