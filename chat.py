"""
Chat über einen Kunden.  Aufruf:  ask("C0010", "Welche Events gab es bei dem Kunden?")

Claude bekommt den kompletten Twin-Kontext (Stammdaten, Haus, IoT, Life Events,
Risiken, Predictions, Empfehlungen) als JSON und beantwortet die Frage daraus.
Claude entscheidet nichts, es erklärt nur, was die Regel-Engine berechnet hat.

API-Key:  Datei .env im Projektordner mit einer Zeile  ANTHROPIC_API_KEY=sk-ant-...
          (oder als Umgebungsvariable exportieren)
"""
import json
import sys
from dataclasses import asdict
from pathlib import Path

import anthropic

from data_loader import load_customer
from digital_twin import DigitalTwin
from models import IoT

CONFIG = Path(__file__).parent / "config.toml"


def _load_dotenv():
    """Liest .env neben dieser Datei und setzt die Variablen, falls noch nicht gesetzt."""
    import os
    env = Path(__file__).parent / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


_load_dotenv()

MODEL = "claude-opus-5-5"

SYSTEM = """Du bist Assistent für einen Allianz-Kundenberater.
Du bekommst den vollständigen Datenkontext eines Kunden als JSON.
Beantworte Fragen des Beraters kurz und sachlich auf Deutsch, nur aus diesem Kontext.
Erfinde keine Daten. Wenn etwas nicht im Kontext steht, sage das.
Zahlen (Wahrscheinlichkeiten, Beträge) immer mit ihren Treibern begründen, die stehen im Kontext.
Empfehlungen nie als Verkaufsdruck formulieren, sondern als Schutz für den Kunden."""


def build_context(twin: DigitalTwin) -> dict:
    """Alles, was der Twin weiß, als ein JSON-Objekt."""
    return {
        "person": asdict(twin.person) | {"age": twin.person.age},
        "house": asdict(twin.house),
        "iot": asdict(twin.iot),
        "life_events": [asdict(e) for e in twin.customer.life_events],
        "risks_12m": {k: asdict(v) for k, v in twin.risks().items()},
        "predicted_events_12m": {k: asdict(v) for k, v in twin.predicted_events().items()},
        "recommendations": [asdict(r) for r in twin.recommendations()],
        "similar_customers_prediction": {k: asdict(v) for k, v in twin.similar_events().items()},
        "regional_trends": {k: {"region": v.region, "label": v.label, "forecast_next_3": v.forecast[:3]}
                            for k, v in twin.regional_trends().items()},
    }


def ask(customer_id: str, prompt: str, history: list | None = None,
        iot: IoT | None = None, contracts: list[str] | None = None) -> str:
    """Eine Frage zu einem Kunden. history = bisherige Nachrichten für Folgefragen."""
    twin = DigitalTwin(load_customer(customer_id, iot=iot, contracts=contracts), config_path=CONFIG)
    context = json.dumps(build_context(twin), default=str, ensure_ascii=False, indent=1)

    messages = list(history or [])
    messages.append({"role": "user", "content": prompt})

    client = anthropic.Anthropic()
    response = client.beta.messages.create(
        model=MODEL,
        max_tokens=2048,
        output_config={"effort": "low"},            # Q&A über gegebenen Kontext, kein tiefes Nachdenken nötig
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",                        # bei Safety-Refusal automatisch anderes Modell
        system=[
            {"type": "text", "text": SYSTEM},
            {"type": "text", "text": f"Kundenkontext (JSON):\n{context}",
             "cache_control": {"type": "ephemeral"}},   # Kontext bleibt gleich → gecacht bei Folgefragen
        ],
        messages=messages,
    )

    if response.stop_reason == "refusal":
        return "Die Anfrage wurde vom Modell abgelehnt."
    answer = "".join(b.text for b in response.content if b.type == "text")
    if history is not None:                         # Verlauf fortschreiben
        history.append({"role": "user", "content": prompt})
        history.append({"role": "assistant", "content": answer})
    return answer


if __name__ == "__main__":
    cid = sys.argv[1] if len(sys.argv) > 1 else "C0010"
    question = sys.argv[2] if len(sys.argv) > 2 else "Welche Life Events gab es bei dem Kunden und was empfiehlst du?"
    print(ask(cid, question, contracts=["hausrat", "haftpflicht_single"]))
