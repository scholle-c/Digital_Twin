from datetime import date

TODAY = date(2026, 10, 23)

# ---------- Beispielkunde: 4 Eingabeblöcke ----------
huber = {
    "person": {"alter": 31, "familienstand": "verheiratet", "kinder": 0, "mieter": True,
               "vertraege": ["hausrat", "haftpflicht_single"]},
    "region": {"plz": "95448", "zuers_zone": 4, "baujahr": 1972},
    "iot": {"rauchmelder": True,
            "alarme": [date(2026, 10, 1), date(2026, 10, 15)],   # Zeitstempel der Alarme
            "batterie_warnung": date(2026, 9, 20)},
    "life_events": [{"typ": "auto", "datum": date(2026, 10, 13)},
                    {"typ": "kind", "datum": date(2026, 10, 16)}],
}


def days_ago(d):
    return (TODAY - d).days


# ---------- 1. Risiko aus Region + IoT ----------
def hazard_risk(c):
    risks = {}
    # Feuer: Basis 0,1 %/Monat, Treiber aus Rauchmelder-Zeitdaten
    f = {}
    if not c["iot"]["rauchmelder"]:
        f["kein Rauchmelder"] = 3.0
    recent_alarms = [a for a in c["iot"]["alarme"] if days_ago(a) < 90]
    if len(recent_alarms) >= 2:
        f[f"{len(recent_alarms)} Alarme in 90 Tagen"] = 2.5
    if c["iot"].get("batterie_warnung") and days_ago(c["iot"]["batterie_warnung"]) > 14:
        f["Batteriewarnung unbeachtet"] = 1.5
    risks["feuer"] = _combine(0.001, f, avg_damage=15000)

    # Hochwasser: Basis 0,05 %/Monat, Treiber aus Region
    f = {}
    z = c["region"]["zuers_zone"]
    if z >= 3:
        f[f"ZÜRS-Zone {z}"] = {3: 4.0, 4: 10.0}[z]
    risks["hochwasser"] = _combine(0.0005, f, avg_damage=8000)
    return risks


def _combine(base_per_month, factors, avg_damage):
    p = base_per_month
    for v in factors.values():
        p *= v
    p12 = 1 - (1 - p) ** 12
    return {"p_12m": round(p12, 3), "expected_damage_eur": round(p12 * avg_damage), "drivers": factors}


# ---------- 2. Prediction: welche Life Events kommen wahrscheinlich? ----------
def predict_life_events(c):
    p, alter, kids = c["person"], c["person"]["alter"], c["person"]["kinder"]
    recent = {e["typ"]: days_ago(e["datum"]) for e in c["life_events"]}
    out = {}

    f = {}
    if 25 <= alter <= 35: f["Alter 25-35"] = 2.0
    if p["mieter"]: f["Mieter"] = 1.5
    if "kind" in recent and recent["kind"] < 365: f["Kind kürzlich geboren"] = 2.5
    out["umzug"] = _combine(0.01, f, avg_damage=0) | {"note": "größere Wohnung"}

    f = {}
    if 25 <= alter <= 38: f["Alter 25-38"] = 2.0
    if p["familienstand"] == "verheiratet": f["verheiratet"] = 1.8
    if kids == 0: f["noch keine Kinder"] = 1.5
    if "kind" in recent and recent["kind"] < 180: f["Kind gerade geboren"] = 0.1
    out["kind"] = _combine(0.01, f, avg_damage=0)

    f = {}
    if "kind" in recent and recent["kind"] < 365: f["Kind kürzlich geboren"] = 2.0
    if "auto" in recent and recent["auto"] < 90: f["Auto gerade gekauft"] = 0.2
    out["auto"] = _combine(0.01, f, avg_damage=0)
    return out


# ---------- 3. Empfehlungen: welche Versicherungen machen Sinn? ----------
def recommend(c, risks, predicted):
    recs, v = [], c["person"]["vertraege"]
    for e in c["life_events"]:
        if e["typ"] == "kind" and "haftpflicht_familie" not in v:
            recs.append((1, "Familienhaftpflicht", f"Kind vor {days_ago(e['datum'])} Tagen geboren, Haftpflicht ist Single"))
        if e["typ"] == "auto" and "kfz" not in v:
            recs.append((1, "Kfz-Versicherung", f"Auto vor {days_ago(e['datum'])} Tagen gekauft"))
    if risks["hochwasser"]["p_12m"] > 0.02 and "elementar" not in v:
        recs.append((2, "Elementarbaustein", f"Hochwasser {risks['hochwasser']['p_12m']:.0%} in 12 Mon., Treiber: {list(risks['hochwasser']['drivers'])}"))
    if risks["feuer"]["p_12m"] > 0.02:
        recs.append((2, "Rauchmelder prüfen", f"Feuerrisiko {risks['feuer']['p_12m']:.0%}, Treiber: {list(risks['feuer']['drivers'])}"))
    if predicted["umzug"]["p_12m"] > 0.3:
        recs.append((3, "Hausrat-Summe bald prüfen", f"Umzug {predicted['umzug']['p_12m']:.0%} wahrscheinlich, Treiber: {list(predicted['umzug']['drivers'])}"))
    return sorted(recs)


if __name__ == "__main__":
    r = hazard_risk(huber)
    le = predict_life_events(huber)
    print("RISIKO:");      [print(" ", k, v) for k, v in r.items()]
    print("LIFE EVENTS:"); [print(" ", k, v) for k, v in le.items()]
    print("EMPFEHLUNGEN:"); [print(" ", x) for x in recommend(huber, r, le)]
