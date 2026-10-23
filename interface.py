"""Command-line interface for customer Digital Twin results."""

import argparse
import os
import time
from pathlib import Path

from data_loader import load_customer
from digital_twin import DigitalTwin


def print_predictions(twin: DigitalTwin) -> None:
    print("\nAktuelle Life Events:")
    if twin.customer.life_events:
        for event in twin.customer.life_events:
            print(f"  {event.type}: {event.date}")
    else:
        print("  keine")

    print("\nRisiken:")
    for risk in twin.risks().values():
        print(
            f"  {risk.label}: {risk.p_12m:.1%}; erwarteter Schaden: "
            f"{risk.expected_damage_eur} EUR; Treiber: {list(risk.drivers)}"
        )

    print("\nLife-Event-Prognosen:")
    for prediction in twin.predicted_events().values():
        print(
            f"  {prediction.label}: {prediction.p_12m:.1%}; "
            f"Treiber: {list(prediction.drivers)}"
        )

    print("\nEmpfehlungen:")
    recommendations = twin.recommendations()
    if recommendations:
        for recommendation in recommendations:
            print(
                f"  [{recommendation.priority}] {recommendation.category}: "
                f"{recommendation.product} - {recommendation.reason}"
            )
    else:
        print("  keine")


def main() -> None:
    os.system("cls" if os.name == "nt" else "clear")
    parser = argparse.ArgumentParser(description="Digital Twin eines Kunden anzeigen.")
    parser.add_argument("customer_id", nargs="?", help="Kunden-ID, z. B. C0001")
    args = parser.parse_args()
    customer_id = args.customer_id or input("Kunden-ID eingeben (z. B. C0001): ").strip()
    if not customer_id:
        parser.error("Eine Kunden-ID ist erforderlich.")

    project_folder = Path(__file__).parent
    try:
        customer = load_customer(customer_id)
    except StopIteration:
        parser.error(f"Kein Kunde mit der ID {customer_id!r} gefunden.")

    config_path = project_folder / "config.toml"
    events_path = project_folder / "generated_demodata" / "life_events.csv"
    twin = DigitalTwin(customer, config_path=config_path)
    last_modified = events_path.stat().st_mtime_ns

    print(f"Digital Twin für {customer_id}; überwache life_events.csv alle 2 Sekunden.")
    print_predictions(twin)

    try:
        while True:
            time.sleep(1)
            modified = events_path.stat().st_mtime_ns
            if modified == last_modified:
                continue

            time.sleep(0.25)
            os.system("cls" if os.name == "nt" else "clear")
            modified = events_path.stat().st_mtime_ns
            customer = load_customer(customer_id)
            twin = DigitalTwin(customer, config_path=config_path)
            last_modified = modified
            print("\nÄnderung erkannt; Digital Twin aktualisiert.")
            print_predictions(twin)
    except KeyboardInterrupt:
        print("\nLive-Ansicht beendet.")


if __name__ == "__main__":
    main()
