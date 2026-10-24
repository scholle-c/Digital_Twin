from pathlib import Path
import tomllib

from models import (
    TODAY,
    Customer,
    EventPrediction,
    House,
    IoT,
    NextBestAction,
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

    def next_best_action(self) -> NextBestAction:
        """Genau eine Handlung für den Berater: Prävention vor Lücke vor Cross-Sell, mit Belegen und Konfidenz.

        Konfidenz: Fakt (gemeldetes Life Event) hoch, Risikoscore mittel, reine Prognose aus ähnlichen Kunden niedrig.
        Ohne ausreichende Evidenz ist das Ergebnis bewusst "keine Aktion".
        """
        # Priorität zuerst (ein gemeldetes Life Event mit Prio 1 schlägt eine allgemeine Prävention mit Prio 2),
        # bei gleicher Priorität Prävention vor Lücke vor Cross-Sell.
        order = {"prevention": 0, "gap": 1, "cross_sell": 2}
        recs = sorted(self.recommendations(), key=lambda r: (r.priority, order.get(r.category, 9)))
        similar = self.similar_events()
        trends = self.regional_trends()
        if not recs:
            weak = [f"{p.event}: {p.p_12m:.0%} laut ähnlichen Kunden" for p in similar.values() if p.p_12m >= 0.5]
            return NextBestAction(
                "none", "Keine Aktion", "", "none", "Nächste Prüfung in 90 Tagen", 0.8,
                "Keine Deckungslücke, kein erhöhtes Risiko und kein aktuelles Life Event erkannt.",
                weak or ["Alle Signale unauffällig"], [],
            )
        top = recs[0]
        signals: list[str] = []
        confidence = {"prevention": 0.7, "gap": 0.75, "cross_sell": 0.6}[top.category]

        # 1. Life Events als Fakt
        recent = [e for e in self.customer.life_events if (TODAY - e.date).days <= 365]
        for e in sorted(recent, key=lambda e: e.date, reverse=True)[:2]:
            signals.append(f"Life Event {e.type} am {e.date:%d.%m.%Y}")
            if top.category == "cross_sell":
                confidence = 0.9
        # 2. Treiber der zugehörigen Gefahr
        for hazard, risk in self.risks().items():
            if risk.drivers and risk.p_12m >= 0.03:
                signals.append(f"{risk.label} {risk.p_12m:.0%} in 12 Mon.: " + ", ".join(risk.drivers))
        # 3. Ähnliche Kunden
        for ev, pred in similar.items():
            hits = [n["id"] for n in pred.neighbors if n["had_event"]]
            if pred.p_12m >= 0.5:
                signals.append(f"{len(hits)} von {len(pred.neighbors)} ähnlichen Kunden hatten {ev} ({', '.join(hits[:3])})")
                confidence = min(1.0, confidence + 0.05)
        # 4. Regionaler Trend
        for metric, tr in trends.items():
            if metric != "kuendigungen" and tr.pct_per_year >= 10:
                signals.append(f"Region {tr.region}: {metric} {tr.label}")

        timing = {1: "Diese Woche", 2: "Diesen Monat", 3: "Beim nächsten Kontakt"}.get(top.priority, "Beim nächsten Kontakt")
        action_type = {"prevention": "risk", "gap": "talk", "cross_sell": "offer"}[top.category]
        label = {"risk": "Risikogespräch", "talk": "Deckungslücke besprechen", "offer": "Angebot unterbreiten"}[action_type]
        return NextBestAction(
            action_type, label, top.product, top.category, timing, round(confidence, 2), top.reason,
            signals[:6], [f"{r.product}: {r.reason}" for r in recs[1:4]],
        )

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