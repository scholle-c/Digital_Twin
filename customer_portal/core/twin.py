"""
Anbindung an den Digital Twin des Projekts (digital_twin.py + config.toml im Projektordner).

Das Portal übergibt die aktuellen Verträge und Fragebogenangaben (z. B. Rauchmelder)
und erhält Risiken, Lebensereignis-Prognosen und Empfehlungen zurück. Ist der Twin
nicht verfügbar, liefert run_twin() None und das Portal nutzt nur seine eigenen Regeln.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass

import streamlit as st

from core.data import DEMO_CUSTOMER_ID, DEMO_DIR, ROOT


# Ergebnis des Twins in einfachen, cachebaren Strukturen.
@dataclass(frozen=True)
class TwinResult:
    """Risiken, Prognosen und Empfehlungen des Digital Twin für den Demokunden."""

    risks: tuple[tuple[str, str, float, int, tuple[str, ...]], ...]
    events: tuple[tuple[str, str, float], ...]
    recommendations: tuple[tuple[int, str, str, str], ...]


# Ruft den Digital Twin auf. Gecacht je Kombination aus Verträgen und Rauchmelder-Angabe.
@st.cache_data(show_spinner=False)
def run_twin(contracts: tuple[str, ...], smoke_detector: bool) -> TwinResult | None:
    """Berechnet Risiken und Empfehlungen; None, falls der Twin nicht geladen werden kann."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    try:
        from data_loader import load_customer
        from digital_twin import DigitalTwin
        from models import IoT

        customer = load_customer(
            DEMO_CUSTOMER_ID, folder=DEMO_DIR, iot=IoT(smoke_detector=smoke_detector), contracts=list(contracts)
        )
        twin = DigitalTwin(customer, config_path=str(ROOT / "config.toml"))
        return TwinResult(
            risks=tuple(
                (r.hazard, r.label, r.p_12m, int(r.expected_damage_eur), tuple(r.drivers)) for r in twin.risks().values()
            ),
            events=tuple((e.event, e.label, e.p_12m) for e in twin.predicted_events().values()),
            recommendations=tuple((r.priority, r.category, r.product, r.reason) for r in twin.recommendations()),
        )
    except Exception:  # noqa: BLE001 – Prototyp: Twin-Fehler dürfen das Portal nicht blockieren
        return None
