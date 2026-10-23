import csv
from datetime import date
from pathlib import Path

from models import Customer, House, IoT, LifeEvent, Person


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def load_customer(
    customer_id: str,
    folder: str | Path | None = None,
    iot: IoT | None = None,
    contracts: list[str] | None = None,
) -> Customer:
    folder = Path(folder) if folder is not None else Path(__file__).parent / "generated_demodata"
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
        ),
        house=House(
            house["building_type"],
            int(house["year"]),
            int(house["riskzone"]),
            house["basement"] == "True",
            int(house["amount_of_floors"]),
        ),
        iot=iot if iot is not None else IoT(),
        life_events=life_events,
    )