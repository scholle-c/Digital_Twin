from dataclasses import dataclass, field
from datetime import date

TODAY = date(2026, 10, 23)


@dataclass
class Person:
    customer_id: str
    age_group: str
    occupation: str
    financial_situation: str
    customer_since: date
    contracts: list[str] = field(default_factory=list)

    @property
    def age(self) -> int:
        lo, hi = self.age_group.split("-")
        return (int(lo) + int(hi)) // 2


@dataclass
class House:
    building_type: str
    year: int
    riskzone: int
    basement: bool
    floors: int


@dataclass
class IoT:
    smoke_detector: bool = False
    alarms: list[date] = field(default_factory=list)
    battery_warning: date | None = None

    def alarms_last(self, days: int) -> int:
        return sum(1 for alarm in self.alarms if (TODAY - alarm).days < days)


@dataclass
class LifeEvent:
    type: str
    date: date


@dataclass
class Customer:
    person: Person
    house: House
    iot: IoT
    life_events: list[LifeEvent]


@dataclass
class Risk:
    hazard: str
    label: str
    p_12m: float
    expected_damage_eur: float
    drivers: dict[str, float]


@dataclass
class EventPrediction:
    event: str
    label: str
    p_12m: float
    drivers: dict[str, float]


@dataclass
class Recommendation:
    priority: int
    category: str
    product: str
    reason: str