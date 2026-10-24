import csv
from datetime import date
from pathlib import Path

from models import Customer, House, IoT, LifeEvent, Person


DATA_FOLDER = Path(__file__).parent / "generated_demodata"


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def _default_smoke_detector(customer_id: str) -> bool:
    idx = int(customer_id[1:]) if customer_id[1:].isdigit() else 0
    return idx % 5 != 0


def _date_or_none(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def load_customer(
    customer_id: str,
    folder: str | Path | None = None,
    iot: IoT | None = None,
    contracts: list[str] | None = None,
) -> Customer:
    folder = Path(folder) if folder is not None else DATA_FOLDER
    customer = next(
        row for row in _read_rows(folder / "customers.csv")
        if row["customer_id"] == customer_id
    )
    house = next(
        row for row in _read_rows(folder / "houses.csv")
        if row["Customer_ID"] == customer_id
    )
    life_events = [
        LifeEvent(row["event_type"], date.fromisoformat(row["event_date"]))
        for row in _read_rows(folder / "life_events.csv")
        if row["customer_id"] == customer_id
    ]

    return Customer(
        person=Person(
            customer["customer_id"],
            customer["age_group"],
            customer["occupation"],
            customer["financial_situation"],
            date.fromisoformat(customer["customer_since"]),
            contracts if contracts is not None else [],
            birth_date=_date_or_none(customer.get("birth_date")),
            gender=customer.get("gender", ""),
            relationship_status=customer.get("relationship_status", ""),
            city=customer.get("residence_city", ""),
            postal_code=customer.get("postal_code", ""),
            federal_state=customer.get("federal_state", ""),
            interests=[i for i in customer.get("interests", "").split(";") if i],
        ),
        house=House(
            house["building_type"],
            int(house["year"]),
            int(house["riskzone"]),
            house["basement"] == "True",
            int(house["amount_of_floors"]),
        ),
        # Demo-Annahme ohne Sensor-CSV: 80 % der Haushalte haben einen Rauchmelder (deterministisch je ID)
        iot=iot if iot is not None else IoT(smoke_detector=_default_smoke_detector(customer_id)),
        life_events=life_events,
    )


# Fiktive Klarnamen, deterministisch aus Kunden-ID und Geschlecht. customers.csv enthält keine Namen.
# Hat das Kundenportal einen Namen in portal_profiles.csv gespeichert, gilt dieser.
FIRST_NAMES = {
    "female": ["Anna", "Lena", "Maria", "Sophie", "Laura", "Julia", "Sarah", "Lisa", "Katharina", "Nina"],
    "male": ["Max", "Lukas", "Jonas", "Felix", "Paul", "Tim", "Jan", "Niklas", "David", "Tobias"],
    "diverse": ["Alex", "Kim", "Robin", "Sascha", "Toni", "Luca", "Noah", "Mika", "Jesse", "Charlie"],
}
LAST_NAMES = ["Bauer", "Müller", "Schmidt", "Schneider", "Fischer", "Weber", "Meyer", "Wagner", "Becker", "Hoffmann"]


# Feste Demo-Personas: diese IDs heißen immer so (Demo-Ablauf).
NAME_OVERRIDES = {"C0021": ("Anna", "Schneider")}   # Anna: 20-29, Studentin, Single, Erlangen


def display_name(customer_id: str, gender: str = "diverse", folder: str | Path | None = None) -> tuple[str, str]:
    """(Vorname, Nachname) für einen Kunden; Demo-Persona, sonst portal_profiles.csv, sonst deterministisch."""
    if customer_id in NAME_OVERRIDES:
        return NAME_OVERRIDES[customer_id]
    folder = Path(folder) if folder is not None else DATA_FOLDER
    overlay = folder / "portal_profiles.csv"
    if overlay.exists():
        row = next((r for r in _read_rows(overlay) if r["customer_id"] == customer_id), None)
        if row and row.get("first_name") and row.get("last_name"):
            return row["first_name"], row["last_name"]
    idx = int(customer_id[1:]) if customer_id[1:].isdigit() else 0
    return FIRST_NAMES.get(gender, FIRST_NAMES["diverse"])[idx % 10], LAST_NAMES[(idx // 10) % 10]


def salutation(gender: str) -> str:
    """Anrede passend zum Geschlecht."""
    return {"female": "Frau", "male": "Herr"}.get(gender, "")


def load_all_customers(folder: str | Path | None = None) -> dict[str, Customer]:
    """Alle Kunden, z. B. für Ähnlichkeitssuche. Ohne IoT und Verträge."""
    folder = Path(folder) if folder is not None else DATA_FOLDER
    ids = [row["customer_id"] for row in _read_rows(folder / "customers.csv")]
    return {cid: load_customer(cid, folder) for cid in ids}


def load_incidents(folder: str | Path | None = None) -> list[dict]:
    """Vorfälle aus incidents.csv: Typ, Datum, Bundesland, PLZ, Schaden."""
    folder = Path(folder) if folder is not None else DATA_FOLDER
    return [
        {
            "type": row["incident_type"],
            "date": date.fromisoformat(row["incident_date"]),
            "region": row["region"],
            "postal_code": row["postal_code"],
            "damage_eur": float(row["damage_eur"] or 0),
            "customer_id": row["customer_id"],
        }
        for row in _read_rows(folder / "incidents.csv")
    ]
