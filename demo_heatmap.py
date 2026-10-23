"""
Proof of Concept: Heatmap mit Zeit-Slider (Vergangenheit, heute, Zukunft).

    .venv/bin/python3 demo_heatmap.py   → schreibt demo_heatmap.html, im Browser öffnen

Daten kommen aus forecast.py (36 Monate Historie + 12 Monate Vorhersage je Region und Kennzahl).
Kundenpunkte werden um die PLZ-Zentren gestreut, damit die Heatmap Fläche hat.
Später in Streamlit:  st.components.v1.html(open("demo_heatmap.html").read(), height=700)
"""
import json
from pathlib import Path

import numpy as np

from data_loader import load_all_customers
from forecast import METRICS, HISTORY_MONTHS, LAST_MONTH, history, forecast, trend_label, regions, _label

FORECAST_MONTHS = 12
CENTERS = {  # Mittelpunkte der Bundesländer
    "Baden-Württemberg": (48.66, 9.35), "Bayern": (48.95, 11.40), "Berlin": (52.52, 13.40),
    "Brandenburg": (52.45, 13.40), "Bremen": (53.08, 8.80), "Hamburg": (53.55, 10.00),
    "Hessen": (50.60, 9.00), "Mecklenburg-Vorpommern": (53.75, 12.50), "Niedersachsen": (52.75, 9.40),
    "Nordrhein-Westfalen": (51.45, 7.60), "Rheinland-Pfalz": (49.95, 7.40), "Saarland": (49.40, 6.95),
    "Sachsen": (51.05, 13.40), "Sachsen-Anhalt": (52.00, 11.70), "Schleswig-Holstein": (54.20, 9.80),
    "Thüringen": (50.90, 11.00),
}
REGIONS = regions()
LABELS = {"kuendigungen": "Vertragsauflösungen", "feueralarme": "Feueralarme (IoT)",
          "einbrueche": "Einbrüche", "wasserschaeden": "Wasserschäden"}
HERE = Path(__file__).parent


def month_labels():
    return [_label(LAST_MONTH, h) for h in range(-HISTORY_MONTHS + 1, FORECAST_MONTHS + 1)]


def series(metric, region):
    """48 Werte: 36 Historie + 12 Forecast, plus Band nur für Forecast."""
    hist = [round(float(v), 2) for v in history(metric, region)]
    fc = forecast(metric, region, FORECAST_MONTHS)
    return {"values": hist + [f["value"] for f in fc],
            "lo": [None] * len(hist) + [f["lo"] for f in fc],
            "hi": [None] * len(hist) + [f["hi"] for f in fc],
            "trend": trend_label(metric, region)}


def customer_points(seed=0):
    """Ein Punkt pro Kunde, um den Mittelpunkt seines Bundeslands gestreut."""
    rng = np.random.default_rng(seed)
    pts = []
    for cid, c in load_all_customers().items():
        region = c.person.federal_state
        if region not in CENTERS:
            continue
        lat, lon = CENTERS[region]
        pts.append({"id": cid, "plz": region,
                    "lat": round(lat + rng.normal(0, 0.35), 4), "lon": round(lon + rng.normal(0, 0.45), 4)})
    return pts


def build():
    data = {
        "months": month_labels(),
        "today_index": HISTORY_MONTHS - 1,
        "metrics": {m: LABELS[m] for m in METRICS},
        "regions": {r: {"lat": CENTERS[r][0], "lon": CENTERS[r][1], "name": ""} for r in REGIONS},
        "series": {m: {r: series(m, r) for r in REGIONS} for m in METRICS},
        "points": customer_points(),
    }
    html = (HERE / "demo_heatmap_template.html").read_text(encoding="utf-8")
    out = HERE / "demo_heatmap.html"
    out.write_text(html.replace("__DATA__", json.dumps(data, ensure_ascii=False)), encoding="utf-8")
    print("geschrieben:", out)


if __name__ == "__main__":
    build()
