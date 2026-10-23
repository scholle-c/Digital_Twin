"""
Vergleich eines Digital Twins mit allen anderen Twins im Bestand.

    portfolio = build_portfolio()
    percentile(portfolio, "C0010", "Feuer")      -> Anteil der anderen Kunden mit niedrigerem Wert (0-100)
    nearest(portfolio, "C0010", k=5)             -> [("C0014", 0.91), ...]
    portfolio.coords                             -> 2D-Position jedes Twins (ähnliche Twins liegen nah beieinander)

Ähnlichkeit kommt aus similarity.py (gewichtete Gower-Ähnlichkeit); die 2D-Karte ist ein
klassisches MDS dieser Ähnlichkeiten.
"""
from dataclasses import dataclass
from pathlib import Path

import numpy as np

import similarity as _similarity
from data_loader import load_all_customers
from digital_twin import DigitalTwin

DEFAULT_CONFIG = Path(__file__).parent / "config.toml"


@dataclass
class TwinSnapshot:
    customer_id: str
    city: str
    age_group: str
    building_type: str
    metrics: dict[str, float]          # Kennzahl -> Wahrscheinlichkeit 12 Monate
    expected_damage_eur: float
    life_events: list[str]
    top_recommendation: str


@dataclass
class Portfolio:
    ids: list[str]
    snapshots: dict[str, TwinSnapshot]
    metric_groups: dict[str, str]      # Kennzahl -> "Risiko" oder "Life Event"
    similarity: np.ndarray             # Ähnlichkeitsmatrix in Reihenfolge von ids
    coords: np.ndarray                 # (n, 2)

    def values(self, metric: str) -> np.ndarray:
        return np.array([self.snapshots[cid].metrics[metric] for cid in self.ids])


def _snapshot(twin: DigitalTwin) -> TwinSnapshot:
    risks = twin.risks()
    events = twin.predicted_events()
    recommendations = twin.recommendations()
    return TwinSnapshot(
        customer_id=twin.person.customer_id,
        city=twin.person.city,
        age_group=twin.person.age_group,
        building_type=twin.house.building_type,
        metrics={r.label: r.p_12m for r in risks.values()} | {e.label: e.p_12m for e in events.values()},
        expected_damage_eur=sum(r.expected_damage_eur for r in risks.values()),
        life_events=[e.type for e in twin.customer.life_events],
        top_recommendation=recommendations[0].product if recommendations else "",
    )


def _classical_mds(similarity: np.ndarray) -> np.ndarray:
    n = len(similarity)
    squared = (1 - similarity) ** 2
    centering = np.eye(n) - np.ones((n, n)) / n
    gram = -0.5 * centering @ squared @ centering
    eigenvalues, eigenvectors = np.linalg.eigh(gram)
    top = np.argsort(eigenvalues)[::-1][:2]
    return eigenvectors[:, top] * np.sqrt(np.maximum(eigenvalues[top], 0))


def build_portfolio(config_path: str | Path = DEFAULT_CONFIG, folder: str | Path | None = None) -> Portfolio:
    customers = load_all_customers(folder)
    ids = list(customers)
    twins = [DigitalTwin(customers[cid], config_path=config_path) for cid in ids]
    snapshots = {cid: _snapshot(twin) for cid, twin in zip(ids, twins)}

    first = twins[0]
    metric_groups = {r.label: "Risiko" for r in first.risks().values()} | {
        e.label: "Life Event" for e in first.predicted_events().values()
    }

    feats = [_similarity.features(customers[cid]) for cid in ids]
    ranges = {
        f: max(v[f] for v in feats) - min(v[f] for v in feats)
        for f, (kind, _) in _similarity.FEATURES.items()
        if kind == "num"
    }
    matrix = np.array([[_similarity.similarity(a, b, ranges) for b in feats] for a in feats])
    return Portfolio(ids, snapshots, metric_groups, matrix, _classical_mds(matrix))


def percentile(portfolio: Portfolio, customer_id: str, metric: str) -> int:
    values = portfolio.values(metric)
    mine = portfolio.snapshots[customer_id].metrics[metric]
    return round(100 * np.sum(values < mine) / max(len(values) - 1, 1))


def nearest(portfolio: Portfolio, customer_id: str, k: int = 5) -> list[tuple[str, float]]:
    row = portfolio.similarity[portfolio.ids.index(customer_id)]
    order = [i for i in np.argsort(row)[::-1] if portfolio.ids[i] != customer_id][:k]
    return [(portfolio.ids[i], round(float(row[i]), 2)) for i in order]


def damage_rank(portfolio: Portfolio, customer_id: str) -> int:
    ranked = sorted(portfolio.ids, key=lambda cid: portfolio.snapshots[cid].expected_damage_eur, reverse=True)
    return ranked.index(customer_id) + 1
