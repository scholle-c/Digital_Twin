from datetime import date
from interface import DigitalTwin, IoT, load_customer

# C0010: 30-39, engineer, high, semi_detached 1986, Zone 3, Kind am 2026-08-02
customer = load_customer(
    "C0010",
    iot=IoT(smoke_detector=True, alarms=[date(2026, 10, 1), date(2026, 10, 15)],
            battery_warning=date(2026, 9, 20)),
    contracts=["hausrat", "haftpflicht_single"],
)
twin = DigitalTwin(customer)

print("PERSON:", twin.person.age, twin.person.occupation, "| Zone", twin.house.riskzone)
print("\nRISIKEN:")
for r in twin.risks().values():
    print(f"  {r.label:25} {r.p_12m:6.1%}  ~{r.expected_damage_eur:>6} €  {list(r.drivers)}")
print("\nLIFE EVENTS (Prediction):")
for e in twin.predicted_events().values():
    print(f"  {e.label:25} {e.p_12m:6.1%}  {list(e.drivers)}")
print("\nEMPFEHLUNGEN:")
for rec in twin.recommendations():
    print(f"  [{rec.priority}] {rec.category:11} {rec.product:28} {rec.reason}")
