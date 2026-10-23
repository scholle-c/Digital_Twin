from pathlib import Path
import tomllib

from models import (
    TODAY,
    Customer,
    EventPrediction,
    House,
    IoT,
    Person,
    Recommendation,
    RegionalTrend,
    Risk,
    SimilarityPrediction,
)
import forecast as _forecast
import similarity as _similarity


class DigitalTwin:
    def __init__(self, customer: Customer, config_path: str = "config.toml"):
        self.customer = customer
        self.config = tomllib.loads(Path(config_path).read_text(encoding="utf-8"))
        self._similar_cache: dict[str, SimilarityPrediction] | None = None

    @property
    def person(self) -> Person:
        return self.customer.person

    @property
    def house(self) -> House:
        return self.customer.house

    @property
    def iot(self) -> IoT:
        return self.customer.iot

    def has(self, product: str) -> bool:
        return product in self.person.contracts

    def days_since(self, event_type: str) -> int | None:
        dates = [event.date for event in self.customer.life_events if event.type == event_type]
        return (TODAY - max(dates)).days if dates else None

    def risks(self) -> dict[str, Risk]:
        output = {}
        for key, config in self.config["hazards"].items():
            probability, drivers = self._evaluate(config)
            output[key] = Risk(
                key,
                config["label"],
                probability,
                round(probability * config["avg_damage_eur"]),
                drivers,
            )
        return output

    def predicted_events(self) -> dict[str, EventPrediction]:
        output = {}
        for key, config in self.config["life_events"].items():
            probability, drivers = self._evaluate(config)
            output[key] = EventPrediction(key, config["label"], probability, drivers)
        return output

    def similar_events(self, k: int = 5) -> dict[str, SimilarityPrediction]:
        """Life Events aus ähnlichen Kunden (similarity.py), mit Nachbarn als Begründung."""
        if self._similar_cache is None:
            self._similar_cache = _similarity.predict_events(self.person.customer_id, k=k)
        return self._similar_cache

    def regional_trends(self, steps: int = 12) -> dict[str, RegionalTrend]:
        """Regionale Kennzahlen (forecast.py) für das Bundesland des Kunden."""
        region = self.person.federal_state
        if region not in _forecast.regions():
            return {}
        return {
            metric: RegionalTrend(
                metric, region,
                round(_forecast.trend_pct(metric, region), 1),
                _forecast.trend_label(metric, region),
                _forecast.forecast(metric, region, steps),
            )
            for metric in _forecast.METRICS
        }

    def recommendations(self) -> list[Recommendation]:
        namespace = self._namespace()
        recommendations = []
        for rule in self.config["recommendations"]:
            if eval(rule["when"], namespace):
                reason = eval(f'f"""{rule["text"]}"""', namespace)
                recommendations.append(
                    Recommendation(
                        rule["priority"], rule["category"], rule["product"], reason
                    )
                )
        return sorted(recommendations, key=lambda recommendation: recommendation.priority)

    def _evaluate(self, config: dict) -> tuple[float, dict[str, float]]:
        namespace = self._namespace()
        drivers = {
            factor["name"]: factor["factor"]
            for factor in config.get("factors", [])
            if eval(factor["when"], namespace)
        }
        monthly_probability = config["base_per_month"]
        for factor in drivers.values():
            monthly_probability *= factor
        return round(1 - (1 - monthly_probability) ** 12, 3), drivers

    def _namespace(self) -> dict:
        return {
            "person": self.person,
            "house": self.house,
            "iot": self.iot,
            "TODAY": TODAY,
            "days_ago": lambda value: (TODAY - value).days,
            "has": self.has,
            "days_since": self.days_since,
            "risk": lambda hazard: self._evaluate(self.config["hazards"][hazard])[0],
            "event_p": lambda event: self._evaluate(self.config["life_events"][event])[0],
            "drivers": lambda hazard: list(
                self._evaluate(self.config["hazards"][hazard])[1]
            ),
            # Neu: Ähnlichkeit und regionaler Trend
            "similar_p": lambda event: self.similar_events().get(event).p_12m if event in self.similar_events() else 0.0,
            "similar_ids": lambda event: [n["id"] for n in self.similar_events()[event].neighbors if n["had_event"]] if event in self.similar_events() else [],
            "trend": lambda metric: self.regional_trends().get(metric).pct_per_year if metric in self.regional_trends() else 0.0,
            "trend_label": lambda metric: self.regional_trends().get(metric).label if metric in self.regional_trends() else "unbekannt",
        }