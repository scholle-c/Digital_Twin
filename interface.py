"""
Digital Twin Interface
----------------------
UI-Gruppe:  erzeugt einen DigitalTwin und liest Properties/Methoden aus.
KI-Gruppe:  passt config.toml an (Raten, Faktoren, Regeln, Texte) oder erweitert
            die Auswertung in _evaluate / _factors.

Alle Zahlen und Regeln stehen in config.toml, nicht im Code.
"""
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
import csv
import tomllib

TODAY = date(2026, 10, 23)


# ============================================================
# 1. EINGABE-OBJEKTE  (4 Kategorien)
# ============================================================
@dataclass
class Person:                       # Stammdaten, aus customers.csv
    customer_id: str
    age_group: str                  # "30-39"
    occupation: str
    financial_situation: str        # low / medium / high
    customer_since: date
    contracts: list[str] = field(default_factory=list)   # z.B. ["hausrat", "haftpflicht_single"]

    @property
    def age(self) -> int:           # Mitte der Altersgruppe, für Regeln
        lo, hi = self.age_group.split("-")
        return (int(lo) + int(hi)) // 2


@dataclass
class House:                        # Region + Gebäude, aus houses.csv
    building_type: str
    year: int
    riskzone: int                   # ZÜRS 1-4
    basement: bool
    floors: int


@dataclass
class IoT:                          # Sensordaten mit Zeitstempeln
    smoke_detector: bool = False
    alarms: list[date] = field(default_factory=list)
    battery_warning: date | None = None

    def alarms_last(self, days: int) -> int:
        return sum(1 for a in self.alarms if (TODAY - a).days < days)


@dataclass
class LifeEvent:                    # aus life_events.csv
    type: str                       # auto / kind / umzug / ...
    date: date


@dataclass
class Customer:
    person: Person
    house: House
    iot: IoT
    life_events: list[LifeEvent]


# ============================================================
# 2. AUSGABE-OBJEKTE
# ============================================================
@dataclass
class Risk:                         # Gefahr: Feuer, Hochwasser, Leitungswasser ...
    hazard: str
    label: str
    p_12m: float                    # Wahrscheinlichkeit nächste 12 Monate
    expected_damage_eur: float
    drivers: dict[str, float]       # Treiber-Name -> Faktor, für Erklärbarkeit


@dataclass
class EventPrediction:              # Life Event: Umzug, Kind, Auto ...
    event: str
    label: str
    p_12m: float
    drivers: dict[str, float]


@dataclass
class Recommendation:
    priority: int                   # 1 = hoch
    category: str                   # prevention / gap / cross_sell
    product: str
    reason: str                     # fertiger Satz für den Berater


# ============================================================
# 3. DER TWIN  (das Objekt, mit dem die UI arbeitet)
# ============================================================
class DigitalTwin:
    def __init__(self, customer: Customer, config_path: str = "config.toml"):
        self.customer = customer
        self.config = tomllib.loads(Path(config_path).read_text())

    # ---- Komfort-Properties für die UI ----
    @property
    def person(self) -> Person: return self.customer.person
    @property
    def house(self) -> House: return self.customer.house
    @property
    def iot(self) -> IoT: return self.customer.iot

    def has(self, product: str) -> bool:
        return product in self.person.contracts

    def days_since(self, event_type: str) -> int | None:
        """Tage seit dem letzten Event dieses Typs, None wenn keins."""
        dates = [e.date for e in self.customer.life_events if e.type == event_type]
        return (TODAY - max(dates)).days if dates else None

    # ---- Die drei Haupt-Ausgaben ----
    def risks(self) -> dict[str, Risk]:
        out = {}
        for key, cfg in self.config["hazards"].items():
            p, drivers = self._evaluate(cfg)
            out[key] = Risk(key, cfg["label"], p, round(p * cfg["avg_damage_eur"]), drivers)
        return out

    def predicted_events(self) -> dict[str, EventPrediction]:
        out = {}
        for key, cfg in self.config["life_events"].items():
            p, drivers = self._evaluate(cfg)
            out[key] = EventPrediction(key, cfg["label"], p, drivers)
        return out

    def recommendations(self) -> list[Recommendation]:
        ns = self._namespace()
        recs = []
        for rule in self.config["recommendations"]:
            if eval(rule["when"], ns):
                reason = eval(f'f"""{rule["text"]}"""', ns)
                recs.append(Recommendation(rule["priority"], rule["category"], rule["product"], reason))
        return sorted(recs, key=lambda r: r.priority)

    # ---- Intern: Basisrate x Faktoren, auf 12 Monate hochgerechnet ----
    def _evaluate(self, cfg) -> tuple[float, dict]:
        ns = self._namespace()
        drivers = {f["name"]: f["factor"] for f in cfg.get("factors", []) if eval(f["when"], ns)}
        p_month = cfg["base_per_month"]
        for f in drivers.values():
            p_month *= f
        return round(1 - (1 - p_month) ** 12, 3), drivers

    def _namespace(self) -> dict:
        """Was in den 'when'- und 'text'-Ausdrücken der Config benutzt werden darf."""
        return {
            "person": self.person, "house": self.house, "iot": self.iot,
            "TODAY": TODAY, "days_ago": lambda d: (TODAY - d).days,
            "has": self.has, "days_since": self.days_since,
            "risk": lambda h: self._evaluate(self.config["hazards"][h])[0],
            "event_p": lambda e: self._evaluate(self.config["life_events"][e])[0],
            "drivers": lambda h: list(self._evaluate(self.config["hazards"][h])[1]),
        }


# ============================================================
# 4. LOADER  (CSV -> Customer)
# ============================================================
def load_customer(customer_id: str, folder: str = ".", iot: IoT | None = None,
                  contracts: list[str] | None = None) -> Customer:
    folder = Path(folder)
    rows = lambda f: list(csv.DictReader(open(folder / f)))
    c = next(r for r in rows("customers.csv") if r["customer_id"] == customer_id)
    h = next(r for r in rows("houses.csv") if r["Customer_ID"] == customer_id)
    ev = [LifeEvent(r["event_type"], date.fromisoformat(r["event_date"]))
          for r in rows("life_events.csv") if r["customer_id"] == customer_id]
    return Customer(
        person=Person(c["customer_id"], c["age_group"], c["occupation"], c["financial_situation"],
                      date.fromisoformat(c["customer_since"]), contracts or []),
        house=House(h["building_type"], int(h["year"]), int(h["riskzone"]),
                    h["basement"] == "True", int(h["amount_of_floors"])),
        iot=iot or IoT(),
        life_events=ev,
    )
