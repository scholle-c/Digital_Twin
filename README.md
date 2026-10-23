# Digital Twin – Schnittstelle

| Datei | Wer | Inhalt |
|---|---|---|
| `models.py` | beide lesen | Eingabe- und Ausgabe-Datenobjekte |
| `data_loader.py` | KI-Gruppe | CSV-Dateien laden und `Customer`-Objekte erstellen |
| `digital_twin.py` | KI-Gruppe | Risiko-, Life-Event- und Empfehlungslogik |
| `interface.py` | UI-Gruppe | Kunden auswählen und Twin-Ergebnisse ausgeben |
| `config.toml` | KI-Gruppe | alle Raten, Faktoren, Regeln, Texte |
| `example.py` | UI-Gruppe als Vorlage | zeigt jeden Aufruf einmal |

## Für die UI-Gruppe

```python
from digital_twin import DigitalTwin
from data_loader import load_customer
from models import IoT
twin = DigitalTwin(load_customer("C0010", iot=IoT(...), contracts=[...]))
```

Die CSV-Dateien liegen in `generated_demodata/`; `load_customer()` verwendet diesen Ordner standardmäßig. Ein alternatives Verzeichnis kann mit `folder=...` übergeben werden.

| Aufruf | Rückgabe |
|---|---|
| `twin.person`, `twin.house`, `twin.iot` | Eingabeobjekte, z. B. `twin.person.age`, `twin.house.riskzone` |
| `twin.has("elementar")` | bool |
| `twin.days_since("kind")` | Tage oder None |
| `twin.risks()` | dict Gefahr → `Risk(label, p_12m, expected_damage_eur, drivers)` |
| `twin.predicted_events()` | dict Event → `EventPrediction(label, p_12m, drivers)` |
| `twin.recommendations()` | Liste `Recommendation(priority, category, product, reason)`, sortiert |

`category` ist `prevention`, `gap` oder `cross_sell` → Farbe in der UI. `drivers` ist die Erklärung.

## Für die KI-Gruppe

Alles in `config.toml`:

- **Neue Gefahr**: Block `[hazards.xyz]` mit `base_per_month`, `avg_damage_eur`, `factors`
- **Neues Life Event**: Block `[life_events.xyz]` mit `base_per_month`, `factors`
- **Neue Empfehlung**: `[[recommendations]]` mit `when` (Python-Ausdruck) und `text` (f-String)
- **Zahlen oder Texte ändern**: direkt im Block

Rechnung: `p_12m = 1 - (1 - base_per_month × alle zutreffenden Faktoren)^12`.
Faktor < 1 senkt, > 1 erhöht. Was in `when`/`text` erlaubt ist, steht oben in `config.toml`.

Neue Eingabefelder (z. B. Wassersensor): Dataclass in `models.py` erweitern, Loader in `data_loader.py` anpassen, dann in `config.toml` nutzen.

## Nicht im Scope
Kein ML, kein LLM in der Entscheidung. Faktoren sind geschätzt, nicht kalibriert.
