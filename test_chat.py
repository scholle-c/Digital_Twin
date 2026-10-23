"""
Testskript für chat.py.  Aufruf:  python3 test_chat.py [KUNDEN_ID]

Stellt drei Fragen zu einem Kunden, die dritte als Folgefrage mit Verlauf.
"""
import os
import sys
from datetime import date

from chat import ask
from models import IoT

customer_id = sys.argv[1] if len(sys.argv) > 1 else "C0010"

if not os.environ.get("ANTHROPIC_API_KEY"):
    sys.exit("Kein API-Key. Lege .env an (siehe .env.example) oder exportiere ANTHROPIC_API_KEY.")

# Demo-Zusatzdaten, die noch nicht in den CSVs stehen
iot = IoT(smoke_detector=True,
          alarms=[date(2026, 10, 1), date(2026, 10, 15)],
          battery_warning=date(2026, 9, 20))
contracts = ["hausrat", "haftpflicht_single"]

questions = [
    "Welche Life Events gab es bei diesem Kunden und wann?",
    "Was sind die drei wichtigsten Empfehlungen und warum?",
]
history = []

for q in questions:
    print(f"\n>>> {q}")
    print(ask(customer_id, q, history=history, iot=iot, contracts=contracts))

# Folgefrage, bezieht sich auf die vorherige Antwort → Verlauf wird mitgeschickt
q = "Und wie würdest du die erste davon dem Kunden am Telefon erklären? Zwei Sätze."
print(f"\n>>> {q}")
print(ask(customer_id, q, history=history, iot=iot, contracts=contracts))

print(f"\n[{len(history)} Nachrichten im Verlauf]")
