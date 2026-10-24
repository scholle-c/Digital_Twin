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
    # neue Felder aus customers.csv (optional, damit alter Code weiterläuft)
    birth_date: date | None = None
    gender: str = ""
    relationship_status: str = ""
    city: str = ""
    postal_code: str = ""
    federal_state: str = ""
    interests: list[str] = field(default_factory=list)

    @property
    def age(self) -> int:
        if self.birth_date:
            return (TODAY - self.birth_date).days // 365
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

@dataclass
class NextBestAction:
    """Eine Handlung für den Berater, abgeleitet aus Regeln, Risiken, Ähnlichkeit und Region."""
    action_type: str                # talk / offer / service / risk / none
    label: str                      # Anzeigename der Handlung
    product: str                    # betroffenes Produkt oder ""
    category: str                   # prevention / gap / cross_sell / none
    timing: str                     # "Diese Woche" / "Diesen Monat" / "Beim nächsten Kontakt" / "Nächste Prüfung in 90 Tagen"
    confidence: float               # 0..1
    reason: str                     # ein Satz
    signals: list[str]              # Belege: Life Events, Treiber, ähnliche Kunden, regionaler Trend
    alternatives: list[str]         # weitere offene Empfehlungen


@dataclass
class SimilarityPrediction:
    """Life Event aus ähnlichen Kunden: p_12m plus die Nachbarn als Begründung."""
    event: str
    p_12m: float
    neighbors: list[dict]           # {"id", "similarity", "had_event", "date"}


@dataclass
class RegionalTrend:
    """Regionale Kennzahl aus forecast.py für die Region des Kunden."""
    metric: str
    region: str
    pct_per_year: float
    label: str                      # "steigend (+13 %/Jahr)"
    forecast: list[dict]            # [{"month", "value", "lo", "hi"}]
