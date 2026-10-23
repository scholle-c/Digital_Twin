"""
Personalisierung: Absicherungsgrad und individuelle Angebote.

Eingaben sind Profil, Fragebogenantworten, Verträge und – falls verfügbar – die
Empfehlungen des Digital Twin. Ändert sich eine Eingabe, berechnen Dashboard und
Angebotsseite beim nächsten Rerun automatisch neu.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from core.data import Policy
from core.twin import TwinResult, run_twin

# Reihenfolge der Kategorien: Fürsorge (Prävention) vor Lücke vor Ergänzung.
CATEGORY_ORDER = {"prevention": 0, "gap": 1, "cross_sell": 2}
CATEGORY_LABELS = {"prevention": "Prävention", "gap": "Lücke schließen", "cross_sell": "Ergänzung"}


# ------------------------------------------------------------
# Eingaben bündeln
# ------------------------------------------------------------

# Verdichtet Profil und Fragebogen zu den Merkmalen, die Regeln und Twin brauchen.
def customer_facts(profile: dict, answers: dict) -> dict:
    """Gibt die für die Personalisierung relevanten Merkmale zurück."""
    children = int(answers.get("children", profile.get("children", 0)) or 0)
    return {
        "children": children,
        "has_partner": profile.get("relationship_status") in ("Verheiratet", "In Partnerschaft"),
        "working": profile.get("occupation") not in ("Rentner/in", "Student/in"),
        "owns_car": answers.get("owns_car", "Ja") == "Ja",
        "owner": answers.get("ownership") == "Eigentum",
        "house": answers.get("housing_type") in ("Reihen-/Doppelhaus", "Freistehendes Haus"),
        "smoke_detector": answers.get("smoke_detector") == "Ja, in allen Räumen",
        "priorities": set(answers.get("priorities", [])),
        "family_changes": set(answers.get("family_change_types", [])),
        "bikes": set(answers.get("bikes", [])),
        "answered": bool(answers),
    }


# Vertragsschlüssel im Format der Twin-Regeln (config.toml), nur aktive bzw. zu prüfende Verträge.
def twin_contracts(policies: list[Policy]) -> tuple[str, ...]:
    """Gibt die Vertragsschlüssel für den Digital Twin zurück."""
    return tuple(sorted(p.twin_key for p in policies if p.twin_key and p.status in ("active", "review")))


# Führt den Twin mit dem aktuellen Stand aus.
def current_twin(policies: list[Policy], facts: dict, customer_id: str) -> TwinResult | None:
    """Berechnet den Twin für den Kunden mit den aktuellen Verträgen und Fragebogenangaben."""
    return run_twin(customer_id, twin_contracts(policies), facts["smoke_detector"])


# ------------------------------------------------------------
# Absicherungsgrad
# ------------------------------------------------------------

# Ein Absicherungsbereich mit Gewicht und Deckungsgrad (0, 0.5 oder 1).
@dataclass
class Need:
    """Bedarfsfeld für die Absicherungsanzeige."""

    key: str
    label: str
    weight: int
    covered: float
    hint: str


# Leitet die relevanten Bedarfsfelder ab und bewertet, wie gut sie abgedeckt sind.
def coverage_needs(policies: list[Policy], facts: dict, twin: TwinResult | None) -> list[Need]:
    """Gibt alle für den Kunden relevanten Bedarfsfelder mit Deckungsgrad zurück."""
    keys = set(twin_contracts(policies))
    family = facts["children"] > 0 or facts["has_partner"]
    flood_risk = any(h == "hochwasser" and p > 0.02 for h, _, p, _, _ in (twin.risks if twin else ()))
    needs = [
        Need("home", "Hausrat", 3, 1.0 if "hausrat" in keys else 0.0, "Schützt Ihre Einrichtung"),
        Need(
            "liability", "Haftpflicht", 3,
            1.0 if "haftpflicht_familie" in keys or ("haftpflicht_single" in keys and not family)
            else 0.5 if "haftpflicht_single" in keys else 0.0,
            "Familie mitversichern" if family and "haftpflicht_familie" not in keys else "Schäden an Dritten",
        ),
        Need("health", "Gesundheit", 2, 1.0 if "kranken_zusatz" in keys else 0.0, "Zusatzleistungen"),
        Need("pension", "Altersvorsorge", 2, 1.0 if "rente" in keys else 0.0, "Einkommen im Alter"),
    ]
    if flood_risk or facts["owner"]:
        needs.append(Need("nature", "Naturgefahren", 2, 1.0 if "elementar" in keys else 0.0, "Starkregen & Hochwasser"))
    if facts["owns_car"]:
        needs.append(Need("mobility", "Mobilität", 2, 1.0 if "kfz" in keys else 0.0, "Ihr Fahrzeug"))
    if facts["working"]:
        needs.append(Need("disability", "Arbeitskraft", 2, 1.0 if "bu" in keys else 0.0, "Berufsunfähigkeit"))
    if facts["children"] > 0 or "Familienschutz" in facts["priorities"]:
        needs.append(Need("family", "Hinterbliebene", 1, 1.0 if "risikoleben" in keys else 0.0, "Familie absichern"))
    return needs


# Gewichteter Absicherungsgrad in Prozent (0–100).
def coverage_score(needs: list[Need]) -> int:
    """Berechnet den Anteil der gewichteten Bedarfsfelder, die abgedeckt sind."""
    total = sum(n.weight for n in needs)
    return round(100 * sum(n.weight * n.covered for n in needs) / total) if total else 0


# ------------------------------------------------------------
# Angebote
# ------------------------------------------------------------

# Ein Eintrag im Angebotskatalog. Preise sind ausdrücklich Beispielwerte.
@dataclass(frozen=True)
class Product:
    """Produkt im Angebotskatalog mit Nutzen, Leistungen und Beispielpreis."""

    id: str
    name: str
    icon: str
    category: str
    need: str
    benefits: tuple[str, ...]
    price: str


CATALOG: dict[str, Product] = {p.id: p for p in [
    Product("familienhaftpflicht", "Privathaftpflicht Familie", "family_restroom", "gap",
            "Ihr Kind und Ihre Partnerin bzw. Ihr Partner sind im Single-Tarif nicht mitversichert.",
            ("Ganze Familie in einem Vertrag", "Deliktunfähige Kinder mitversichert", "Umstellung ohne Lücke"),
            "ab 2,10 € mehr pro Monat"),
    Product("elementar", "Elementarschutz für Ihren Hausrat", "flood", "gap",
            "Starkregen und Hochwasser sind in Ihrer Hausratversicherung nicht eingeschlossen.",
            ("Überschwemmung und Rückstau", "Schneedruck und Erdrutsch", "Als Baustein zum bestehenden Vertrag"),
            "ab 3,50 € pro Monat"),
    Product("rauchmelder", "Rauchmelder-Check & Smart Home", "detector_smoke", "prevention",
            "Rauchmelder senken das Brandrisiko deutlich – laut Ihrem Twin fehlen sie noch.",
            ("Vernetzte Rauchmelder", "Warnung aufs Smartphone", "Kostenlose Montage-Anleitung"),
            "Service ohne Beitrag"),
    Product("wassersensor", "Wassersensor-Paket", "water_drop", "prevention",
            "Ein Wassersensor meldet Leitungswasserschäden, bevor sie groß werden.",
            ("Sensor für Bad und Keller", "Push-Benachrichtigung", "Rabatt auf die Hausrat"),
            "ab 1,90 € pro Monat"),
    Product("hausrat_check", "Hausrat-Summe prüfen", "fact_check", "gap",
            "Bei Umzug oder Nachwuchs wächst oft der Wert Ihres Hausrats.",
            ("Online-Wertermittlung in 3 Minuten", "Schutz vor Unterversicherung", "Anpassung jederzeit"),
            "kostenloser Check"),
    Product("kfz", "Kfz-Versicherung", "directions_car", "gap",
            "Für Ihr Fahrzeug ist bei uns noch kein Vertrag hinterlegt.",
            ("Haftpflicht, Teil- oder Vollkasko", "Schutzbrief inklusive", "SF-Rabatt übertragbar"),
            "ab 39 € pro Monat"),
    Product("wohngebaeude", "Wohngebäudeversicherung", "home", "gap",
            "Als Eigentümer tragen Sie Schäden am Gebäude selbst.",
            ("Feuer, Leitungswasser, Sturm, Hagel", "Optional Elementarschutz", "Neuwert-Erstattung"),
            "ab 24 € pro Monat"),
    Product("risikoleben", "Risikolebensversicherung", "favorite", "cross_sell",
            "Sichert Ihre Familie finanziell ab, falls Ihnen etwas zustößt.",
            ("Feste Summe für Hinterbliebene", "Laufzeit passend zur Familienplanung", "Niedrige Beiträge in jungen Jahren"),
            "ab 8,90 € pro Monat"),
    Product("kinderunfall", "Kinderunfallversicherung", "child_care", "cross_sell",
            "Kinder sind in der gesetzlichen Unfallversicherung nur in Kita und Schule geschützt.",
            ("Schutz rund um die Uhr", "Leistung bei bleibenden Schäden", "Reha-Management"),
            "ab 5,80 € pro Monat"),
    Product("bu", "Berufsunfähigkeitsversicherung", "work", "cross_sell",
            "Ihre Arbeitskraft ist Ihr wichtigstes Kapital – und bisher nicht abgesichert.",
            ("Monatliche Rente bei Berufsunfähigkeit", "Verzicht auf abstrakte Verweisung", "Nachversicherung bei Lebensereignissen"),
            "ab 45 € pro Monat"),
    Product("rechtsschutz", "Rechtsschutzversicherung", "gavel", "cross_sell",
            "Finanzielle Sicherheit auch dann, wenn es zum Rechtsstreit kommt.",
            ("Privat-, Berufs- und Verkehrsrecht", "Telefonische Erstberatung", "Mediation inklusive"),
            "ab 19 € pro Monat"),
    Product("reise", "Auslandsreise-Krankenversicherung", "flight", "cross_sell",
            "Für Reisen ins Ausland – die gesetzliche Kasse zahlt dort oft nur teilweise.",
            ("Weltweiter Schutz", "Rücktransport inklusive", "Für die ganze Familie"),
            "ab 1,20 € pro Monat"),
    Product("fahrrad", "Fahrrad- & E-Bike-Schutz", "pedal_bike", "cross_sell",
            "Ihr Hausrat deckt Fahrraddiebstahl nur bis 1.500 €.",
            ("Diebstahl rund um die Uhr", "Akku- und Elektronikschäden", "Pannenhilfe"),
            "ab 6,50 € pro Monat"),
    Product("nachhaltig", "Nachhaltige Altersvorsorge", "eco", "cross_sell",
            "Ihnen ist Nachhaltigkeit wichtig – das geht auch bei der Vorsorge.",
            ("Fonds mit Nachhaltigkeitsfokus", "Flexible Beiträge", "Transparente Berichte"),
            "ab 25 € pro Monat"),
]}

# Ordnet Produktnamen aus config.toml (Twin-Empfehlungen) dem Katalog zu.
TWIN_PRODUCTS = {
    "Familienhaftpflicht": "familienhaftpflicht", "Elementarbaustein": "elementar",
    "Rauchmelder prüfen": "rauchmelder", "Wassersensor anbieten": "wassersensor",
    "Hausrat-Summe bald prüfen": "hausrat_check", "Kfz-Versicherung": "kfz",
}


# Ein konkretes, begründetes Angebot für den Kunden.
@dataclass
class Offer:
    """Personalisiertes Angebot mit Begründung und Herkunft der Empfehlung."""

    product: Product
    reason: str
    source: str
    priority: int
    sources: list[str] = field(default_factory=list)


# Erzeugt die Angebotsliste aus Twin-Empfehlungen und eigenen Regeln; ohne Dubletten, priorisiert.
def build_offers(policies: list[Policy], facts: dict, twin: TwinResult | None) -> list[Offer]:
    """Gibt die priorisierten, begründeten Angebote für den Kunden zurück."""
    keys = set(twin_contracts(policies))
    offers: dict[str, Offer] = {}

    def add(product_id: str, reason: str, source: str, priority: int) -> None:
        if product_id in offers:
            offers[product_id].sources.append(source)
            return
        offers[product_id] = Offer(CATALOG[product_id], reason, source, priority, [source])

    # 1. Empfehlungen des Digital Twin (Regeln aus config.toml).
    for priority, _category, product, reason in (twin.recommendations if twin else ()):
        if product in TWIN_PRODUCTS:
            add(TWIN_PRODUCTS[product], reason, "Digital Twin", priority)

    # 2. Ergänzende Regeln aus Profil und Fragebogen.
    if facts["children"] > 0 and "haftpflicht_familie" not in keys:
        add("familienhaftpflicht", f"{facts['children']} Kind(er) im Haushalt, Haftpflicht im Single-Tarif", "Profil", 1)
    if facts["owns_car"] and "kfz" not in keys:
        add("kfz", "Laut Fragebogen besitzen Sie ein Auto", "Fragebogen", 2)
    if facts["owner"] and facts["house"] and "wohngebaeude" not in keys:
        add("wohngebaeude", "Sie wohnen im eigenen Haus", "Fragebogen", 2)
    if facts["working"] and "bu" not in keys:
        add("bu", "Sie sind berufstätig und haben keine Berufsunfähigkeitsabsicherung", "Profil", 3)
    if (facts["children"] > 0 or "Familienschutz" in facts["priorities"]) and "risikoleben" not in keys:
        add("risikoleben", "Familienschutz ist Ihnen wichtig" if "Familienschutz" in facts["priorities"]
            else "Sie haben Kinder im Haushalt", "Profil" if not facts["answered"] else "Fragebogen", 3)
    if facts["children"] > 0 or "Geburt / Adoption" in facts["family_changes"]:
        add("kinderunfall", "Ihre Familie ist gewachsen", "Profil", 4)
    if "Finanzielle Sicherheit" in facts["priorities"]:
        add("rechtsschutz", "Finanzielle Sicherheit ist Ihnen wichtig", "Fragebogen", 4)
    if "Reisen" in facts["priorities"]:
        add("reise", "Reisen ist eines Ihrer Themen", "Fragebogen", 4)
    if "Nachhaltigkeit" in facts["priorities"]:
        add("nachhaltig", "Nachhaltigkeit ist Ihnen wichtig", "Fragebogen", 5)
    if facts["bikes"] & {"E-Bike", "Lastenrad"}:
        add("fahrrad", "Sie fahren E-Bike bzw. Lastenrad", "Fragebogen", 4)

    return sorted(offers.values(), key=lambda o: (CATEGORY_ORDER[o.product.category], o.priority, o.product.name))
