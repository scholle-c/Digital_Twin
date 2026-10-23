"""
Life-Event-Prediction über ähnliche Kunden (k nächste Nachbarn).  Nutzt data_loader, nur numpy.

    from similarity import predict_events
    predict_events("C0010", k=5)
    -> {"kind": SimilarityPrediction(event="kind", p_12m=0.6, neighbors=[{"id": "C0014", "similarity": 0.91, ...}]), ...}

  1. Jeder Kunde wird ein Merkmalsvektor (Alter, Finanzen, Beziehung, Kunde seit, Haus, bisherige Events).
  2. Ähnlichkeit = 1 - gewichtete Gower-Distanz (Zahlen normiert, Kategorien 0/1).
  3. Anteil der k ähnlichsten Kunden mit dem Event in den letzten 12 Monaten, gewichtet nach Ähnlichkeit.
     Beim Vorhersagen von Event X wird das Merkmal had_X weggelassen (Leakage).
"""
from data_loader import DATA_FOLDER, load_all_customers
from models import TODAY, Customer, SimilarityPrediction

# Alle Kunden werden einmal geladen und wiederverwendet, bis sich eine CSV ändert.
# Ohne diesen Cache liest jeder Twin alle CSVs neu (bei 250 Kunden: 250 x 0,2 s pro Portfolio-Aufbau).
_customers_cache: dict = {"stamp": None, "customers": None}


def all_customers() -> dict[str, Customer]:
    """Gecachte Kundenliste; lädt neu, sobald eine CSV in generated_demodata geändert wurde."""
    stamp = max((f.stat().st_mtime for f in DATA_FOLDER.glob("*.csv")), default=None)
    if _customers_cache["stamp"] != stamp:
        _customers_cache.update(stamp=stamp, customers=load_all_customers())
    return _customers_cache["customers"]

EVENT_TYPES = ["kind", "auto"]
WINDOW_DAYS = 730   # Demo-Daten: nur 1 Event pro Kunde, daher 24 Monate; bei echten Daten 365

FEATURES = {                                   # Merkmal: (Typ, Gewicht)
    "age":                 ("num", 3.0),
    "financial":           ("num", 2.0),
    "years_customer":      ("num", 1.0),
    "relationship_status": ("cat", 2.0),
    "building_type":       ("cat", 1.5),
    "house_age":           ("num", 1.0),
    "basement":            ("cat", 0.5),
    "had_kind":            ("cat", 2.0),
    "had_auto":            ("cat", 1.0),
}


def features(c: Customer) -> dict:
    return {
        "age": c.person.age,
        "financial": {"low": 0, "medium": 1, "high": 2}.get(c.person.financial_situation, 1),
        "years_customer": (TODAY - c.person.customer_since).days / 365,
        "relationship_status": c.person.relationship_status,
        "building_type": c.house.building_type,
        "house_age": TODAY.year - c.house.year,
        "basement": c.house.basement,
        "had_kind": any(e.type == "kind" for e in c.life_events),
        "had_auto": any(e.type == "auto" for e in c.life_events),
    }


def similarity(a: dict, b: dict, ranges: dict, exclude: str | None = None) -> float:
    total, weight_sum = 0.0, 0.0
    for f, (kind, w) in FEATURES.items():
        if f == exclude:
            continue
        d = abs(a[f] - b[f]) / ranges[f] if kind == "num" and ranges[f] else (0.0 if a[f] == b[f] else 1.0) if kind == "cat" else 0.0
        total += w * d
        weight_sum += w
    return 1 - total / weight_sum


def predict_events(customer_id: str, k: int = 5, customers: dict[str, Customer] | None = None,
                   events: list[str] = EVENT_TYPES) -> dict[str, SimilarityPrediction]:
    customers = customers or all_customers()
    feats = {cid: features(c) for cid, c in customers.items()}
    ranges = {f: max(v[f] for v in feats.values()) - min(v[f] for v in feats.values())
              for f, (kind, _) in FEATURES.items() if kind == "num"}
    me = feats[customer_id]

    out = {}
    for ev in events:
        scored = sorted(((similarity(me, feats[cid], ranges, exclude=f"had_{ev}"), cid)
                         for cid in customers if cid != customer_id), reverse=True)[:k]
        rows, num, den = [], 0.0, 0.0
        for sim, cid in scored:
            recent = [e.date for e in customers[cid].life_events if e.type == ev and (TODAY - e.date).days <= WINDOW_DAYS]
            num += sim * bool(recent)
            den += sim
            rows.append({"id": cid, "similarity": round(sim, 2), "had_event": bool(recent),
                         "date": recent[0].isoformat() if recent else None})
        out[ev] = SimilarityPrediction(ev, round(num / den, 2) if den else 0.0, rows)
    return out


if __name__ == "__main__":
    import sys
    cid = sys.argv[1] if len(sys.argv) > 1 else "C0010"
    c = all_customers()[cid]
    print(f"{cid}: {c.person.age} J., {c.person.relationship_status}, {c.person.city}, {c.house.building_type}\n")
    for ev, p in predict_events(cid).items():
        print(f"{ev.upper():5} in 12 Monaten: {p.p_12m:.0%}")
        for n in p.neighbors:
            print(f"   {n['id']}  Ähnlichkeit {n['similarity']:.2f}  {'ja, ' + n['date'] if n['had_event'] else 'nein'}")
