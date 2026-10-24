"""
KI-Funktionen des Dashboards: Gesprächsbericht und Chat, beides über chat.py im Projektordner.

Läuft ohne API-Key weiter: die Funktionen geben dann None bzw. eine Fehlermeldung zurück und
die Oberfläche zeigt den regelbasierten Leitfaden.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))
import chat as _chat  # noqa: E402  (lädt .env)


def ai_available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _data_stamp() -> float:
    folder = PROJECT_ROOT / "generated_demodata"
    return max((f.stat().st_mtime for f in folder.glob("*.csv")), default=0.0)


@st.cache_data(show_spinner=False)
def _report(customer_id: str, lang: str, name: str, stamp: float) -> str | None:
    try:
        return _chat.prepare_report(customer_id, lang="Deutsch" if lang == "de" else "English", name=name)
    except Exception as error:  # noqa: BLE001 – Prototyp: KI-Fehler blockieren die Seite nicht
        return f"__error__:{error}"


def conversation_report(customer_id: str, lang: str, name: str) -> str | None:
    """Gecachter Gesprächsbericht; None ohne Key, Fehlertext beginnt mit __error__."""
    if not ai_available():
        return None
    return _report(customer_id, lang, name, _data_stamp())


def chat_answer(customer_id: str, prompt: str, history: list[dict]) -> str:
    """Antwort auf eine Beraterfrage zum Kunden; schreibt den Verlauf fort."""
    try:
        return _chat.ask(customer_id, prompt, history=history)
    except Exception as error:  # noqa: BLE001
        return f"Der Chat ist gerade nicht erreichbar: {error}"
