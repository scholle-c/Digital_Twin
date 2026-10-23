"""
Regionale Zeitreihen + Vorhersage x Monate in die Zukunft.  Nur numpy.

    from forecast import forecast, trend_label, heatmap_frame
    forecast("einbrueche", "Bayern", steps=6)
    -> [{"month": "2026-11", "value": 4.1, "lo": 2.9, "hi": 5.3}, ...]

Regionen = Bundesländer aus customers.csv.
Historie = synthetische Grundlinie (Trend + Saison + Rauschen) PLUS echte Vorfälle aus incidents.csv,
           gezählt pro Region und Monat. Sobald genug echte Daten da sind, Grundlinie auf 0 setzen.
Modell = lineare Regression (Trend) + Monats-Saisonalität, Band aus Residuen-Streuung.
"""
import zlib
from collections import Counter

import numpy as np

from data_loader import load_all_customers, load_incidents

HISTORY_MONTHS = 36
LAST_MONTH = (2026, 10)

METRICS = {
    # name: (Grundlinie, Trend/Monat, Saison-Amplitude, Rauschen, incident_types aus incidents.csv)
    "kuendigungen":   (3.0, 0.08, 0.5, 0.6, []),
    "feueralarme":    (5.0, 0.15, 1.0, 1.0, ["fire", "lightning_surge"]),
    "einbrueche":     (2.0, 0.02, 1.2, 0.5, ["burglary", "attempted_burglary", "theft"]),
    "wasserschaeden": (4.0, 0.05, 0.8, 0.8, ["water_damage"]),
}

_customers = None
_incidents = None

# Trend-Multiplikator je Bundesland (Demo-Annahme, frei änderbar). 1.0 = Basistrend aus METRICS.
REGION_TREND = {
    "Bayern": 3.0, "Nordrhein-Westfalen": 2.5, "Berlin": 2.0, "Hessen": 1.5,
    "Baden-Württemberg": 1.0, "Niedersachsen": 0.5, "Sachsen": 0.0, "Hamburg": -0.3,
    "Schleswig-Holstein": -0.6, "Bremen": -0.8, "Rheinland-Pfalz": -1.0,
    "Brandenburg": 1.0, "Thüringen": 0.0, "Sachsen-Anhalt": -0.5, "Saarland": 0.5, "Mecklenburg-Vorpommern": 0.0,
}


def regions() -> list[str]:
    """Bundesländer, in denen Kunden wohnen, alphabetisch."""
    global _customers
    if _customers is None:
        _customers = load_all_customers()
    return sorted({c.person.federal_state for c in _customers.values() if c.person.federal_state})


def customers_in(region: str) -> list[str]:
    return [cid for cid, c in (_customers or load_all_customers()).items() if c.person.federal_state == region]


# ---------- 1. Historie: Grundlinie + echte Vorfälle ----------
def history(metric: str, region: str) -> np.ndarray:
    global _incidents
    base, trend, season_amp, noise, incident_types = METRICS[metric]
    rng = np.random.default_rng(zlib.crc32(f"{metric}|{region}".encode()))   # deterministisch über Prozesse
    region_factor = 1 + 0.3 * (regions().index(region) % 4) if region in regions() else 1.0
    # Demo: Regionen entwickeln sich unterschiedlich (stark steigend, leicht steigend, stabil, fallend),
    # damit Vergangenheit und Prognose auf der Karte sichtbar auseinanderlaufen.
    region_trend = REGION_TREND.get(region, 1.0)
    t = np.arange(HISTORY_MONTHS)
    months = (t + _month_index(LAST_MONTH) - HISTORY_MONTHS + 1) % 12
    season = season_amp * np.cos(2 * np.pi * months / 12)
    y = base * region_factor + trend * region_trend * t + season + rng.normal(0, noise, HISTORY_MONTHS)

    if incident_types:
        if _incidents is None:
            _incidents = load_incidents()
        counts = Counter(_months_back(i["date"]) for i in _incidents
                         if i["region"] == region and i["type"] in incident_types)
        for back, n in counts.items():
            if 0 <= back < HISTORY_MONTHS:
                y[HISTORY_MONTHS - 1 - back] += n
    return np.maximum(y, 0)


# ---------- 2. Modell: Trend + Saison ----------
def fit(y: np.ndarray):
    t = np.arange(len(y))
    slope, intercept = np.polyfit(t, y, 1)
    detrended = y - (slope * t + intercept)
    months = (t + _month_index(LAST_MONTH) - len(y) + 1) % 12
    season = np.array([detrended[months == m].mean() for m in range(12)])
    resid_std = (detrended - season[months]).std()
    return slope, intercept, season, resid_std


# ---------- 3. Vorhersage ----------
def forecast(metric: str, region: str, steps: int = 6) -> list[dict]:
    y = history(metric, region)
    slope, intercept, season, resid_std = fit(y)
    out = []
    for h in range(1, steps + 1):
        t = len(y) - 1 + h
        value = max(slope * t + intercept + season[(_month_index(LAST_MONTH) + h) % 12], 0.0)
        band = 1.96 * resid_std * np.sqrt(1 + h / len(y))
        out.append({"month": _label(LAST_MONTH, h), "value": round(float(value), 2),
                    "lo": round(float(max(value - band, 0)), 2), "hi": round(float(value + band), 2)})
    return out


def trend_pct(metric: str, region: str) -> float:
    """Änderung pro Jahr in Prozent des Mittelwerts."""
    y = history(metric, region)
    slope = fit(y)[0]
    return float(12 * slope / max(y.mean(), 1e-6) * 100)


def trend_label(metric: str, region: str) -> str:
    pct = trend_pct(metric, region)
    word = "steigend" if pct > 5 else "fallend" if pct < -5 else "stabil"
    return f"{word} ({pct:+.0f} %/Jahr)"


def heatmap_frame(metric: str, step: int) -> dict[str, float]:
    """Ein Wert pro Region. step < 0 Vergangenheit, 0 letzter Monat, > 0 Vorhersage."""
    out = {}
    for r in regions():
        if step <= 0:
            out[r] = round(float(history(metric, r)[HISTORY_MONTHS - 1 + step]), 2)
        else:
            out[r] = forecast(metric, r, step)[-1]["value"]
    return out


def _month_index(ym): return ym[1] - 1
def _label(ym, h):
    y, m = ym[0], ym[1] - 1 + h
    return f"{y + m // 12}-{m % 12 + 1:02d}"
def _months_back(d): return (LAST_MONTH[0] - d.year) * 12 + (LAST_MONTH[1] - d.month)


if __name__ == "__main__":
    print("Regionen:", regions())
    m, r = "einbrueche", "Bayern"
    print(f"\n{m} in {r}, letzte 6 Monate:", np.round(history(m, r)[-6:], 1), "|", trend_label(m, r))
    for row in forecast(m, r, 3):
        print(f"  {row['month']}  {row['value']:5.1f}  [{row['lo']:.1f} … {row['hi']:.1f}]")
    print("\nHeatmap +6 Monate:", heatmap_frame(m, 6))
