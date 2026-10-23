"""
Demo- und Stammdaten des Kundenportals.

Der Demokunde „Max Bauer“ basiert auf Kunde C0010 aus generated_demodata/customers.csv.
Name, Adresse, Kontaktdaten und Verträge sind frei erfunden. Regionale Vorfälle und
Naturereignisse stammen aus den synthetischen CSV-Dateien des Projekts.
"""
from __future__ import annotations

import csv
import math
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

# Projektwurzel (enthält digital_twin.py, config.toml und generated_demodata/).
ROOT = Path(__file__).resolve().parents[2]
DEMO_DIR = ROOT / "generated_demodata"

# Stichtag des Prototyps; identisch mit TODAY in models.py.
TODAY = date(2026, 10, 23)

# Demo-Zugang. Bewusst offen dokumentiert – es werden keine echten Zugangsdaten verarbeitet.
DEMO_CUSTOMER_ID = "C0010"
DEMO_LOGIN = {"customer_number": "DT-100010", "email": "max.bauer@example.com", "password": "demo"}

# Koordinaten des Wohnorts für Umkreisberechnungen (Würzburg).
HOME_COORDS = (49.7913, 9.9534)


# ------------------------------------------------------------
# Profil
# ------------------------------------------------------------

# Übersetzt Codes aus den CSV-Dateien in lesbare deutsche Begriffe.
OCCUPATIONS = {
    "engineer": "Ingenieur/in", "office_worker": "Bürokaufmann/-frau", "student": "Student/in",
    "retired": "Rentner/in", "teacher": "Lehrer/in", "manager": "Führungskraft",
    "self_employed": "Selbstständig", "healthcare_worker": "Gesundheitswesen",
}
RELATIONSHIP = {
    "married": "Verheiratet", "partnership": "In Partnerschaft", "single": "Ledig",
    "divorced": "Geschieden", "widowed": "Verwitwet",
}
INTERESTS = {
    "cycling": "Radfahren", "home_improvement": "Heimwerken", "technology": "Technik",
    "travel": "Reisen", "hiking": "Wandern", "cooking": "Kochen", "music": "Musik",
}


# Liest die Zeile des Demokunden aus customers.csv; fehlt die Datei, gelten Standardwerte.
def _demo_customer_row() -> dict[str, str]:
    """Gibt die CSV-Zeile des Demokunden oder ein leeres Dict zurück."""
    path = DEMO_DIR / "customers.csv"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as file:
        return next((row for row in csv.DictReader(file) if row["customer_id"] == DEMO_CUSTOMER_ID), {})


# Erzeugt das bearbeitbare Profil. Persönliche Angaben sind fiktiv, Lebenslage stammt aus den Demodaten.
def initial_profile() -> dict:
    """Gibt das Startprofil des Demokunden als Dict zurück."""
    row = _demo_customer_row()
    interests = [INTERESTS.get(i, i) for i in row.get("interests", "cycling;technology").split(";")]
    return {
        "first_name": "Max",
        "last_name": "Bauer",
        "customer_number": DEMO_LOGIN["customer_number"],
        "birth_date": date.fromisoformat(row.get("birth_date", "1990-05-14")),
        "street": "Lindenweg 12",
        "postal_code": row.get("postal_code", "97082"),
        "city": row.get("residence_city", "Würzburg"),
        "email": DEMO_LOGIN["email"],
        "phone": "+49 151 00000000",
        "relationship_status": RELATIONSHIP.get(row.get("relationship_status", "married"), "Verheiratet"),
        "children": 1,
        "household_size": 3,
        "occupation": OCCUPATIONS.get(row.get("occupation", "engineer"), "Ingenieur/in"),
        "interests": interests,
        "channels": ["E-Mail", "App-Benachrichtigung"],
        "contact_time": "Abends",
        "newsletter": False,
    }


# ------------------------------------------------------------
# Verträge
# ------------------------------------------------------------

# Ein fiktiver Versicherungsvertrag. "twin_key" ist der Schlüssel, den die Regeln in config.toml kennen.
@dataclass
class Policy:
    """Versicherungsvertrag des Demokunden mit Eckdaten und Leistungsübersicht."""

    id: str
    name: str
    product_line: str
    icon: str
    status: str
    policy_number: str
    start: date
    renewal: date | None
    premium_month: float
    coverage: dict[str, str]
    review_note: str = ""
    twin_key: str = ""
    documents: list[str] = field(default_factory=list)


# Ausgangsbestand. Bedingungen und Beiträge sind Beispielwerte, keine echten Tarife.
def initial_policies() -> list[Policy]:
    """Gibt die fiktiven Verträge des Demokunden zurück."""
    return [
        Policy(
            "hausrat", "Hausratversicherung", "Wohnen", "chair", "review", "HR-4471-2209",
            date(2022, 10, 3), date(2026, 12, 1), 9.80,
            {"Versicherungssumme": "65.000 €", "Selbstbeteiligung": "150 €", "Fahrraddiebstahl": "bis 1.500 €",
             "Elementarschäden": "nicht eingeschlossen"},
            "Elementarschäden (Starkregen, Hochwasser) sind nicht eingeschlossen. Ihr Wohnort liegt in einer erhöhten Gefährdungszone.",
            "hausrat", ["Versicherungsschein 2022", "Beitragsrechnung 2026"],
        ),
        Policy(
            "haftpflicht", "Privathaftpflicht", "Haftung", "shield_person", "review", "PH-1180-5532",
            date(2022, 10, 3), date(2027, 10, 3), 5.40,
            {"Tarif": "Single", "Deckungssumme": "10 Mio. €", "Schlüsselverlust": "eingeschlossen",
             "Mitversicherte Personen": "keine"},
            "Seit der Geburt Ihres Kindes sind Familienmitglieder nicht mitversichert. Ein Familientarif schließt die Lücke.",
            "haftpflicht_single", ["Versicherungsschein 2022"],
        ),
        Policy(
            "kfz", "Kfz-Versicherung", "Mobilität", "directions_car", "active", "KF-7742-0391",
            date(2023, 1, 1), date(2027, 1, 1), 54.20,
            {"Fahrzeug": "Kompaktklasse, Elektro", "Umfang": "Haftpflicht + Teilkasko", "SF-Klasse": "SF 8",
             "Jährliche Fahrleistung": "12.000 km"},
            "", "kfz", ["Versicherungsschein 2023", "Beitragsrechnung 2026"],
        ),
        Policy(
            "kranken", "Krankenzusatzversicherung", "Gesundheit", "health_and_safety", "active", "KZ-3305-7716",
            date(2023, 4, 1), None, 32.60,
            {"Stationär": "Zweibettzimmer, Chefarzt", "Zahn": "Zahnersatz bis 80 %", "Brille": "bis 150 € alle 2 Jahre"},
            "", "kranken_zusatz", ["Versicherungsschein 2023"],
        ),
        Policy(
            "rente", "Private Rentenversicherung", "Vorsorge", "savings", "active", "RV-9021-4458",
            date(2022, 12, 1), None, 150.00,
            {"Beitrag": "150 € / Monat", "Geplanter Rentenbeginn": "2058 (Beispiel)", "Dynamik": "3 % pro Jahr"},
            "", "rente", ["Standmitteilung 2026"],
        ),
    ]


# Anzeige der Vertragsstatus: Text, Symbol und Farbvariante (nie nur Farbe).
POLICY_STATUS = {
    "active": ("Aktiv", "check_circle", "ok"),
    "review": ("Prüfung empfohlen", "error", "warn"),
    "requested": ("Angefragt", "schedule", "info"),
}


# ------------------------------------------------------------
# Regionale Demodaten (CSV)
# ------------------------------------------------------------

# Gruppiert Vorfallarten aus incidents.csv zu verständlichen Risikokategorien.
INCIDENT_GROUPS = {
    "burglary": "Einbruch & Diebstahl", "attempted_burglary": "Einbruch & Diebstahl",
    "theft": "Einbruch & Diebstahl", "bicycle_theft": "Einbruch & Diebstahl", "vehicle_theft": "Einbruch & Diebstahl",
    "fire": "Feuer & Elektro", "lightning_surge": "Feuer & Elektro",
    "water_damage": "Leitungswasser",
    "vandalism": "Vandalismus & Glas", "glass_breakage": "Vandalismus & Glas",
    "cyber_fraud": "Cyber & Betrug",
}
DISASTER_LABELS = {
    "heavy_rain": "Starkregen", "flood": "Hochwasser", "storm": "Sturm", "hail": "Hagel", "heatwave": "Hitze",
    "wildfire": "Waldbrand", "earthquake": "Erdbeben", "landslide": "Erdrutsch", "avalanche": "Lawine",
    "snow_load": "Schneelast", "volcanic_eruption": "Vulkanausbruch",
}
INCIDENT_LABELS = {
    "burglary": "Einbruch", "attempted_burglary": "Einbruchsversuch", "theft": "Diebstahl",
    "bicycle_theft": "Fahrraddiebstahl", "vehicle_theft": "Kfz-Diebstahl", "fire": "Brand",
    "lightning_surge": "Überspannung", "water_damage": "Leitungswasser", "vandalism": "Vandalismus",
    "glass_breakage": "Glasbruch", "cyber_fraud": "Online-Betrug",
}


# Lädt incidents.csv (Einbruch, Brand, Wasser …) mit lesbaren Kategorien. Leer, falls die Datei fehlt.
@st.cache_data(show_spinner=False)
def load_incidents() -> pd.DataFrame:
    """Gibt die synthetischen Schadenereignisse als DataFrame zurück."""
    path = DEMO_DIR / "incidents.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path, dtype={"postal_code": str, "customer_id": str})
    df["incident_date"] = pd.to_datetime(df["incident_date"])
    df["group"] = df["incident_type"].map(INCIDENT_GROUPS).fillna("Sonstiges")
    df["label"] = df["incident_type"].map(INCIDENT_LABELS).fillna(df["incident_type"])
    return df


# Lädt disaster.csv (Naturereignisse in Europa) mit deutschen Bezeichnungen.
@st.cache_data(show_spinner=False)
def load_disasters() -> pd.DataFrame:
    """Gibt die synthetischen Naturereignisse als DataFrame zurück."""
    path = DEMO_DIR / "disaster.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    df["start_date"] = pd.to_datetime(df["start_date"])
    df["label"] = df["disaster_type"].map(DISASTER_LABELS).fillna(df["disaster_type"])
    return df


# Verknüpft Schäden und Krankheitsfälle mit der Altersgruppe der Kunden (für demografische Trends).
@st.cache_data(show_spinner=False)
def load_age_group_claims() -> pd.DataFrame:
    """Gibt je Altersgruppe die Anzahl Sach- und Gesundheitsfälle zurück."""
    customers_path = DEMO_DIR / "customers.csv"
    if not customers_path.exists():
        return pd.DataFrame()
    customers = pd.read_csv(customers_path)[["customer_id", "age_group"]]
    frames = []
    incidents = load_incidents()
    if not incidents.empty:
        frames.append(incidents.dropna(subset=["customer_id"]).assign(kind="Sachschäden")[["customer_id", "kind"]])
    illnesses_path = DEMO_DIR / "illnesses.csv"
    if illnesses_path.exists():
        frames.append(pd.read_csv(illnesses_path).assign(kind="Gesundheitsfälle")[["customer_id", "kind"]])
    if not frames:
        return pd.DataFrame()
    merged = pd.concat(frames).merge(customers, on="customer_id")
    return merged.groupby(["age_group", "kind"]).size().reset_index(name="count")


# Luftlinie zwischen zwei Koordinaten in Kilometern (Haversine-Formel).
def distance_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Berechnet die Entfernung zwischen zwei (Breite, Länge)-Punkten in km."""
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


# ------------------------------------------------------------
# Mitteilungen
# ------------------------------------------------------------

# Baut die Start-Mitteilungen; zwei davon werden aus den regionalen Demodaten abgeleitet.
def initial_notifications(postal_code: str) -> list[dict]:
    """Gibt die Mitteilungen beim Login zurück (neueste zuerst)."""
    notes = []
    disasters = load_disasters()
    if not disasters.empty:
        upcoming = disasters[disasters["status"].isin(["active", "forecast"]) & (disasters["country"] == "DE")].copy()
        upcoming["km"] = upcoming.apply(lambda r: distance_km(HOME_COORDS, (r.latitude, r.longitude)), axis=1)
        for _, r in upcoming[upcoming["km"] <= 150].sort_values("km").iterrows():
            when = "aktuell" if r.status == "active" else f"ab {r.start_date:%d.%m.}"
            notes.append({
                "id": f"dis_{r.disaster_id}", "category": "warning", "date": TODAY,
                "title": f"{r.label} bei {r.city} ({when})",
                "text": f"Rund {r.km:.0f} km von Ihrem Wohnort entfernt. Prüfen Sie Keller und Abflüsse.",
                "page": "trends", "read": False,
            })
    incidents = load_incidents()
    if not incidents.empty:
        near = incidents[incidents["postal_code"].str[:3] == postal_code[:3]]
        recent = near[(pd.Timestamp(TODAY) - near["incident_date"]).dt.days <= 90]
        if not recent.empty:
            notes.append({
                "id": "nbh_incidents", "category": "warning", "date": recent["incident_date"].max().date(),
                "title": f"{len(recent)} Vorfall/Vorfälle in Ihrer Nachbarschaft",
                "text": "In Ihrem PLZ-Gebiet wurde in den letzten 90 Tagen eingebrochen. Tipps zum Einbruchschutz finden Sie unter Trends.",
                "page": "trends", "read": False,
            })
    notes += [
        {"id": "renewal_hausrat", "category": "contract", "date": date(2026, 10, 20),
         "title": "Ihre Hausratversicherung verlängert sich am 01.12.2026",
         "text": "Ein guter Zeitpunkt, um Versicherungssumme und Elementarschutz zu prüfen.", "page": "insurance", "read": False},
        {"id": "questionnaire", "category": "system", "date": date(2026, 10, 18),
         "title": "Fragebogen „Ihre Lebenssituation“ ausstehend",
         "text": "Mit wenigen Angaben werden Ihre Empfehlungen deutlich genauer.", "page": "questionnaire", "read": False},
        {"id": "invoice_2027", "category": "contract", "date": date(2026, 10, 2),
         "title": "Neues Dokument: Beitragsübersicht 2027", "text": "Ihre Beitragsübersicht steht im Postfach bereit.",
         "page": "insurance", "read": True},
    ]
    return notes
