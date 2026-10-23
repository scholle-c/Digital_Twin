"""Command-line interface for customer Digital Twin results."""

import argparse
from pathlib import Path

from data_loader import load_customer
from digital_twin import DigitalTwin


def print_predictions(twin: DigitalTwin) -> None:
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


if __name__ == "__main__":
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

    twin = DigitalTwin(customer, config_path=project_folder / "config.toml")
    print(f"Digital Twin für {customer_id}")
    print_predictions(twin)
