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
    Risk,
)


class DigitalTwin:
    def __init__(self, customer: Customer, config_path: str = "config.toml"):
        self.customer = customer
        self.config = tomllib.loads(Path(config_path).read_text(encoding="utf-8"))

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
        }