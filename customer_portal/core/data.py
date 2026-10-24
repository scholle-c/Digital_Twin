"""
Demo- und Stammdaten des Kundenportals.

Profil, Lebenslage und Region kommen aus generated_demodata/customers.csv und life_events.csv.
Name, Adresse und Kontaktdaten gibt es dort nicht; sie werden fiktiv erzeugt und beim Speichern
in portal_profiles.csv abgelegt. Verträge sind weiterhin fiktiv (keine Vertrags-CSV vorhanden).
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
import sys as _sys
if str(ROOT) not in _sys.path:
    _sys.path.insert(0, str(ROOT))
from data_loader import display_name  # noqa: E402  (gleiche Klarnamen wie im Berater-Dashboard)

# Stichtag des Prototyps; identisch mit TODAY in models.py.
TODAY = date(2026, 10, 23)

# Demo-Zugang: jede Kunden-ID aus customers.csv (z. B. C0010) mit dem festen Passwort "demo".
DEMO_PASSWORD = "demo"

# Mittelpunkte der Bundesländer als Rückfall für den Wohnort, wenn keine PLZ-Koordinaten bekannt sind.
STATE_CENTERS = {
    "Baden-Württemberg": (48.66, 9.35), "Bayern": (48.95, 11.40), "Berlin": (52.52, 13.40),
    "Brandenburg": (52.45, 13.40), "Bremen": (53.08, 8.80), "Hamburg": (53.55, 10.00),
    "Hessen": (50.60, 9.00), "Mecklenburg-Vorpommern": (53.75, 12.50), "Niedersachsen": (52.75, 9.40),
    "Nordrhein-Westfalen": (51.45, 7.60), "Rheinland-Pfalz": (49.95, 7.40), "Saarland": (49.40, 6.95),
    "Sachsen": (51.05, 13.40), "Sachsen-Anhalt": (52.00, 11.70), "Schleswig-Holstein": (54.20, 9.80),
    "Thüringen": (50.90, 11.00),
}


# ------------------------------------------------------------
# Profil
# ------------------------------------------------------------

# Übersetzt Codes aus den CSV-Dateien in lesbare deutsche Begriffe (vollständig für customers.csv).
OCCUPATIONS = {
    "apprentice": "Auszubildende/r", "craft_worker": "Handwerker/in", "designer": "Designer/in",
    "engineer": "Ingenieur/in", "healthcare_worker": "Gesundheitswesen", "manager": "Führungskraft",
    "office_worker": "Bürokaufmann/-frau", "public_sector": "Öffentlicher Dienst", "retail_worker": "Einzelhandel",
    "retired": "Rentner/in", "sales": "Vertrieb", "self_employed": "Selbstständig",
    "skilled_worker": "Facharbeiter/in", "student": "Student/in", "teacher": "Lehrer/in",
}
RELATIONSHIP = {
    "married": "Verheiratet", "partnership": "In Partnerschaft", "single": "Ledig",
    "divorced": "Geschieden", "widowed": "Verwitwet",
}
INTERESTS = {
    "art": "Kunst", "camping": "Camping", "cars": "Autos", "cooking": "Kochen", "cycling": "Radfahren",
    "fashion": "Mode", "fishing": "Angeln", "fitness": "Fitness", "football": "Fußball", "gaming": "Gaming",
    "gardening": "Garten", "golf": "Golf", "hiking": "Wandern", "home_improvement": "Heimwerken",
    "horse_riding": "Reiten", "motorcycling": "Motorrad", "music": "Musik", "online_shopping": "Online-Shopping",
    "pets": "Haustiere", "photography": "Fotografie", "reading": "Lesen", "running": "Laufen",
    "sailing": "Segeln", "skiing": "Skifahren", "technology": "Technik", "travel": "Reisen",
    "wine": "Wein", "yoga": "Yoga",
}
# Rückübersetzung deutsch -> CSV-Code für das Speichern.
OCCUPATION_CODES = {v: k for k, v in OCCUPATIONS.items()}
RELATIONSHIP_CODES = {v: k for k, v in RELATIONSHIP.items()}
INTEREST_CODES = {v: k for k, v in INTERESTS.items()}


# Spalten, die nur das Portal kennt (nicht in customers.csv). Liegen in portal_profiles.csv.
PORTAL_FIELDS = ["first_name", "last_name", "street", "email", "phone", "children", "household_size",
                 "channels", "contact_time", "newsletter"]


def _read_csv(name: str) -> list[dict[str, str]]:
    """Liest eine CSV aus generated_demodata als Liste von Dicts; leer, falls sie fehlt."""
    path = DEMO_DIR / name
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def customer_ids() -> list[str]:
    """Alle Kunden-IDs aus customers.csv."""
    return [row["customer_id"] for row in _read_csv("customers.csv")]


def customer_row(customer_id: str) -> dict[str, str]:
    """Gibt die CSV-Zeile eines Kunden zurück oder ein leeres Dict."""
    return next((row for row in _read_csv("customers.csv") if row["customer_id"] == customer_id), {})


def _portal_row(customer_id: str) -> dict[str, str]:
    """Portal-eigene Felder (Name, Adresse, Kontakt) aus portal_profiles.csv, falls vorhanden."""
    return next((row for row in _read_csv("portal_profiles.csv") if row["customer_id"] == customer_id), {})


def age_group_for(birth: date) -> str:
    """Altersgruppe im Format der CSV (z. B. "30-39") aus dem Geburtsdatum."""
    age = (TODAY - birth).days // 365
    lo = max(age // 10 * 10, 20) if age >= 20 else 18
    return f"{lo}-{lo + 9}" if age >= 20 else "18-19"


def home_coords(postal_code: str, federal_state: str = "") -> tuple[float, float]:
    """Koordinaten des Wohnorts: Mittel der Vorfälle mit gleicher PLZ, sonst Bundesland-Mitte."""
    incidents = load_incidents()
    if not incidents.empty:
        same = incidents[incidents["postal_code"] == postal_code]
        if not same.empty:
            return float(same["latitude"].mean()), float(same["longitude"].mean())
    return STATE_CENTERS.get(federal_state, (51.2, 10.4))


# Erzeugt das bearbeitbare Profil aus customers.csv, life_events.csv und (falls vorhanden) portal_profiles.csv.
def initial_profile(customer_id: str) -> dict:
    """Gibt das Startprofil eines Kunden als Dict zurück."""
    row = customer_row(customer_id)
    extra = _portal_row(customer_id)
    gender = row.get("gender", "diverse")
    first, last = display_name(customer_id, gender)
    children = sum(1 for e in _read_csv("life_events.csv") if e["customer_id"] == customer_id and e["event_type"] == "kind")
    relationship = RELATIONSHIP.get(row.get("relationship_status", "single"), "Ledig")
    partner = relationship in ("Verheiratet", "In Partnerschaft")
    interests = [INTERESTS.get(i, i) for i in row.get("interests", "").split(";") if i]
    birth = date.fromisoformat(row["birth_date"]) if row.get("birth_date") else date(1990, 1, 1)
    since = date.fromisoformat(row["customer_since"]) if row.get("customer_since") else TODAY
    return {
        "customer_id": customer_id,
        "customer_number": customer_id,
        "customer_since": since,
        "federal_state": row.get("federal_state", ""),
        "first_name": first,
        "last_name": last,
        "birth_date": birth,
        "street": extra.get("street") or "Musterstraße 1",
        "postal_code": row.get("postal_code", "00000"),
        "city": row.get("residence_city", ""),
        "email": extra.get("email") or f"{customer_id.lower()}@example.com",
        "phone": extra.get("phone") or "+49 151 00000000",
        "relationship_status": relationship,
        "children": int(extra["children"]) if extra.get("children") else children,
        "household_size": int(extra["household_size"]) if extra.get("household_size") else 1 + int(partner) + children,
        "occupation": OCCUPATIONS.get(row.get("occupation", "office_worker"), row.get("occupation", "")),
        "interests": interests,
        "channels": extra["channels"].split(";") if extra.get("channels") else ["E-Mail", "App-Benachrichtigung"],
        "contact_time": extra.get("contact_time") or "Abends",
        "newsletter": extra.get("newsletter") == "True" if extra.get("newsletter") else False,
    }


# ------------------------------------------------------------
# Rückschreiben in die CSV-Dateien (Source of Truth)
# ------------------------------------------------------------

def _write_csv(name: str, rows: list[dict], fieldnames: list[str]) -> None:
    """Schreibt eine CSV vollständig neu, gleiche Spaltenreihenfolge wie beim Lesen."""
    with (DEMO_DIR / name).open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def save_profile_to_csv(profile: dict) -> None:
    """Überträgt das Profil in customers.csv (bekannte Spalten) und portal_profiles.csv (Portal-Felder)."""
    cid = profile["customer_id"]
    rows = _read_csv("customers.csv")
    if rows:
        for row in rows:
            if row["customer_id"] == cid:
                row["birth_date"] = profile["birth_date"].isoformat()
                row["age_group"] = age_group_for(profile["birth_date"])
                row["postal_code"] = profile["postal_code"]
                row["residence_city"] = profile["city"]
                if profile.get("federal_state"):
                    row["federal_state"] = profile["federal_state"]
                row["relationship_status"] = RELATIONSHIP_CODES.get(profile["relationship_status"], row["relationship_status"])
                row["occupation"] = OCCUPATION_CODES.get(profile["occupation"], row["occupation"])
                row["interests"] = ";".join(INTEREST_CODES.get(i, i) for i in profile["interests"])
        _write_csv("customers.csv", rows, list(rows[0].keys()))

    extra_rows = [r for r in _read_csv("portal_profiles.csv") if r["customer_id"] != cid]
    extra_rows.append({"customer_id": cid, **{
        f: (";".join(profile[f]) if isinstance(profile[f], list) else str(profile[f])) for f in PORTAL_FIELDS
    }})
    extra_rows.sort(key=lambda r: r["customer_id"])
    _write_csv("portal_profiles.csv", extra_rows, ["customer_id", *PORTAL_FIELDS])
    st.cache_data.clear()   # Twin-Ergebnisse und CSV-Caches neu berechnen


EVENT_LABELS = {"umzug": "Umzug", "kind": "Geburt eines Kindes", "auto": "Autokauf", "hund": "Hund angeschafft",
                "heirat": "Heirat", "ebike": "E-Bike gekauft"}
FEDERAL_STATES = ["Baden-Württemberg", "Bayern", "Berlin", "Brandenburg", "Bremen", "Hamburg", "Hessen",
                  "Mecklenburg-Vorpommern", "Niedersachsen", "Nordrhein-Westfalen", "Rheinland-Pfalz", "Saarland",
                  "Sachsen", "Sachsen-Anhalt", "Schleswig-Holstein", "Thüringen"]


def life_events_of(customer_id: str) -> list[dict]:
    """Gemeldete Lebensereignisse eines Kunden aus life_events.csv, neueste zuerst."""
    rows = [r for r in _read_csv("life_events.csv") if r["customer_id"] == customer_id]
    return sorted(({"type": r["event_type"], "label": EVENT_LABELS.get(r["event_type"], r["event_type"]),
                    "date": date.fromisoformat(r["event_date"])} for r in rows), key=lambda e: e["date"], reverse=True)


def add_life_event(customer_id: str, event_type: str, event_date: date) -> None:
    """Hängt ein Lebensereignis an life_events.csv an (Source of Truth) und leert die Caches."""
    rows = _read_csv("life_events.csv")
    next_id = max((int(r["event_id"][1:]) for r in rows if r["event_id"][1:].isdigit()), default=0) + 1
    rows.append({"event_id": f"E{next_id:04d}", "customer_id": customer_id, "event_type": event_type,
                 "event_date": event_date.isoformat()})
    _write_csv("life_events.csv", rows, ["event_id", "customer_id", "event_type", "event_date"])
    st.cache_data.clear()


# ------------------------------------------------------------
# Meine Region: Kennzahlen aus den Kundendaten der Umgebung
# ------------------------------------------------------------

LOOKING = {"single", "divorced", "widowed"}


def _region_customers(profile: dict) -> tuple[str, list[dict]]:
    """Feinste Region mit mindestens 10 Kunden: PLZ-Gebiet (erste 2 Ziffern), sonst Bundesland."""
    rows = _read_csv("customers.csv")
    prefix = profile["postal_code"][:2]
    area = [r for r in rows if r["postal_code"][:2] == prefix]
    if len(area) >= 10:
        cities = sorted({r["residence_city"] for r in area})
        label = f"PLZ-Gebiet {prefix} ({', '.join(cities[:3])}{' …' if len(cities) > 3 else ''})"
        return label, area
    state = profile.get("federal_state", "")
    return state or "Deutschland", [r for r in rows if r["federal_state"] == state] or rows


def region_insights(profile: dict) -> dict:
    """Aussagen über die Region des Kunden: Sicherheit, Singles, Altersgruppe, Interessen, Naturgefahr."""
    label, area = _region_customers(profile)
    everyone = _read_csv("customers.csv")
    n, n_all = len(area), len(everyone)

    def share(rows, pred):
        return sum(1 for r in rows if pred(r)) / max(len(rows), 1)

    my_age = profile.get("age_group") or age_group_for(profile["birth_date"])
    singles = share(area, lambda r: r["relationship_status"] in LOOKING)
    singles_all = share(everyone, lambda r: r["relationship_status"] in LOOKING)
    same_age = share(area, lambda r: r["age_group"] == my_age)
    same_age_all = share(everyone, lambda r: r["age_group"] == my_age)
    interests: dict[str, int] = {}
    for r in area:
        for i in r["interests"].split(";"):
            if i:
                interests[i] = interests.get(i, 0) + 1
    top_interests = [INTERESTS.get(k, k) for k, _ in sorted(interests.items(), key=lambda kv: -kv[1])[:3]]

    # Sicherheit: Einbrüche/Diebstähle der letzten 12 Monate je 100 Kunden, Region vs. Deutschland
    incidents = load_incidents()
    state = profile.get("federal_state", "")
    crime_region = crime_all = 0.0
    if not incidents.empty:
        recent = incidents[(pd.Timestamp(TODAY) - incidents["incident_date"]).dt.days <= 365]
        theft = recent[recent["group"] == "Einbruch & Diebstahl"]
        n_state = sum(1 for r in everyone if r["federal_state"] == state) or 1
        crime_region = 100 * len(theft[theft["region"] == state]) / n_state
        crime_all = 100 * len(theft) / max(n_all, 1)
    disasters = load_disasters()
    nearby = 0
    if not disasters.empty:
        d = disasters[(disasters["country"] == "DE") & disasters["status"].isin(["active", "forecast"])]
        nearby = int((d["region"] == state).sum())
    try:
        import sys as _s
        if str(ROOT) not in _s.path:
            _s.path.insert(0, str(ROOT))
        import forecast as fc
        trend = fc.trend_label("einbrueche", state) if state in fc.regions() else ""
    except Exception:  # noqa: BLE001
        trend = ""

    return {
        "label": label, "n": n, "state": state, "my_age": my_age,
        "singles": singles, "singles_all": singles_all,
        "same_age": same_age, "same_age_all": same_age_all,
        "top_interests": top_interests,
        "crime_region": crime_region, "crime_all": crime_all, "crime_trend": trend,
        "nearby_disasters": nearby,
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
def initial_notifications(postal_code: str, coords: tuple[float, float]) -> list[dict]:
    """Gibt die Mitteilungen beim Login zurück (neueste zuerst)."""
    notes = []
    disasters = load_disasters()
    if not disasters.empty:
        upcoming = disasters[disasters["status"].isin(["active", "forecast"]) & (disasters["country"] == "DE")].copy()
        upcoming["km"] = upcoming.apply(lambda r: distance_km(coords, (r.latitude, r.longitude)), axis=1)
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
