"""
Synthetische Mockdaten für den Customer-360-Prototyp.

Alle Personen, Verträge und Ereignisse sind frei erfunden. Die Datenklassen
legen die Struktur fest, die später durch echte Quellen (Vertragsbestand,
Digital Twin aus ../interface.py, Content Enrichment, Modellwahrscheinlichkeiten)
befüllt werden kann. Die Darstellung liest ausschließlich diese Strukturen,
dadurch bleibt der Austausch der Datenquelle unabhängig von der Oberfläche.
"""
from __future__ import annotations

from dataclasses import dataclass, field


# ============================================================
# Datenmodell
# ============================================================

# Beschreibt eine fachliche Kategorie (Prävention, Deckungslücke, Cross-Sell).
# "order" bildet die verbindliche Priorisierung ab: Fürsorge vor Vertrieb.
@dataclass(frozen=True)
class Category:
    """Fachliche Kategorie einer Empfehlung inklusive Anzeigename und Rangfolge."""

    key: str
    label: str
    order: int
    description: str


# Beschreibt den Status einer Versicherung. Symbol und Text werden immer
# zusammen angezeigt, damit der Status nie nur über Farbe erkennbar ist.
@dataclass(frozen=True)
class CoverageStatus:
    """Anzeigestatus einer Versicherungssparte (Text, Symbol und CSS-Variante)."""

    key: str
    label: str
    symbol: str


# Kennzahl im Kopf der Versicherungsdetailseite (z. B. „Vertragsstatus: Nicht enthalten“).
# "tone" steuert die Farbe: danger, warning, info oder ok.
@dataclass
class Kpi:
    """Kurze Statuskennzahl mit Bezeichnung, Wert, Symbol und Farbton."""

    label: str
    value: str
    icon: str
    tone: str


# Ein Signal aus dem Content Enrichment: Prognose mit Wahrscheinlichkeit und Herkunft.
# Später liefert hier das Modell bzw. die Enrichment-Pipeline die Werte.
@dataclass
class Signal:
    """Modellbasierte Einschätzung (0–1) mit Titel, verwendeten Merkmalen und Symbol."""

    title: str
    probability: float
    sources: list[str]
    icon: str


# Ein Grund im Bereich „Warum diese Einschätzung?“ mit aufklappbarer Erläuterung.
@dataclass
class Reason:
    """Begründung aus einer Datenquelle inklusive Kurztext und ausführlicher Erläuterung."""

    icon: str
    title: str
    summary: str
    detail: str = ""
    show_contract: bool = False


# Eine Versicherungssparte des Kunden. Übersicht und Versicherungsdetailseite
# lesen ausschließlich aus diesem Objekt.
@dataclass
class Coverage:
    """Versicherungssparte eines Kunden mit Vertrag, Prognosen, Begründungen und Empfehlung."""

    key: str
    label: str
    icon: str
    status: str
    contract: dict[str, str] = field(default_factory=dict)
    recommendation: str = ""
    sources: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    # Ausführlicher Name im Kopf der Detailseite, z. B. „Elementarschutz“.
    title: str = ""
    kpis: list[Kpi] = field(default_factory=list)
    # Ergebnisse aus dem Content Enrichment, sortiert nach Wahrscheinlichkeit.
    signals: list[Signal] = field(default_factory=list)
    reasons: list[Reason] = field(default_factory=list)
    action_title: str = ""
    benefit: str = ""
    # Kategorie der Handlungsempfehlung (prevention, gap, cross_sell) oder None für neutral.
    action_category: str | None = None
    action_icon: str = ""
    consent: str = "Nutzung der Vertragsdaten im Rahmen der bestehenden Kundenbeziehung."

    # Ergänzt fehlende Angaben mit Standardwerten passend zum Status, damit auch
    # Verträge ohne Auffälligkeiten eine vollständige Detailseite erhalten.
    def __post_init__(self) -> None:
        """Füllt Titel, Kennzahlen, Begründungen und Empfehlungstitel mit Standardwerten."""
        self.title = self.title or self.label
        self.action_icon = self.action_icon or self.icon
        if not self.kpis:
            self.kpis = DEFAULT_KPIS[self.status]
        if not self.reasons:
            summary = "Baustein enthalten" if self.status == "protected" else "Baustein nicht enthalten"
            self.reasons = [Reason("file", "Vertragsdaten", summary, show_contract=True)]
        if not self.action_title:
            self.action_title = (
                "Kein akuter Handlungsbedarf" if self.status == "protected"
                else "Bei nächster Gelegenheit ansprechen"
            )


# Ein Eintrag der Ereignis-Timeline im Kundendetail.
@dataclass
class Event:
    """Ereignis in der Kundenhistorie, z. B. Wetterwarnung oder Umzug."""

    when: str
    title: str
    icon: str
    is_new: bool = False


# Zentraler Kundendatensatz. Jede Komponente der Oberfläche liest nur aus
# diesem Objekt, fachliche Texte stehen damit an genau einer Stelle.
@dataclass
class Customer:
    """Vollständiger Kundendatensatz für Liste, Detailansicht und Gesprächsvorbereitung."""

    id: str
    name: str
    salutation: str
    age: int
    city: str
    housing: str
    priority: int
    category: str
    urgency: str
    topic_icon: str
    reason: str
    headline: str
    situation: list[str]
    recommendation: str
    benefit: str
    last_contact: str
    sources: list[str]
    explanation: list[str]
    coverages: list[Coverage]
    events: list[Event]
    conversation_opening: str
    conversation_questions: list[str]
    conversation_goal: str


# ============================================================
# Stammdaten für Darstellung und Priorisierung
# ============================================================

# Kategorien in fachlicher Reihenfolge: 1 = Prävention, 2 = Deckungslücke, 3 = Cross-Sell.
# Die Schlüssel entsprechen den Kategorien aus ../interface.py (prevention, gap, cross_sell).
CATEGORIES: dict[str, Category] = {
    "prevention": Category("prevention", "PRÄVENTION", 1, "Schäden verhindern"),
    "gap": Category("gap", "DECKUNGSLÜCKE", 2, "Deckungslücken schließen"),
    "cross_sell": Category("cross_sell", "CROSS-SELL", 3, "Passende Ergänzungen anbieten"),
}

# Mögliche Status einer Versicherungssparte mit Text und ergänzendem Symbol.
COVERAGE_STATUS: dict[str, CoverageStatus] = {
    "protected": CoverageStatus("protected", "Geschützt", "check"),
    "check": CoverageStatus("check", "Lücke prüfen", "alert"),
    "missing": CoverageStatus("missing", "Nicht vorhanden", "minus"),
}

# Standard-Kennzahlen je Status für Versicherungen ohne eigene Angaben.
DEFAULT_KPIS: dict[str, list[Kpi]] = {
    "protected": [
        Kpi("Vertragsstatus", "Enthalten", "file", "ok"),
        Kpi("Aktuelle Risikolage", "Unauffällig", "shield", "ok"),
        Kpi("Handlungsbedarf", "Keiner", "calendar", "ok"),
    ],
    "check": [
        Kpi("Vertragsstatus", "Prüfen", "file", "warning"),
        Kpi("Aktuelle Risikolage", "Unklar", "warning", "info"),
        Kpi("Handlungsbedarf", "Bei Gelegenheit", "calendar", "info"),
    ],
    "missing": [
        Kpi("Vertragsstatus", "Nicht vorhanden", "file", "info"),
        Kpi("Aktuelle Risikolage", "Unauffällig", "shield", "ok"),
        Kpi("Handlungsbedarf", "Bei Gelegenheit", "calendar", "info"),
    ],
}

# Angemeldeter Berater (Hauptnutzer des Prototyps).
ADVISOR = {"first_name": "Markus", "last_name": "Weber"}


# ============================================================
# Synthetische Kundendaten
# ============================================================

# Liste aller Kunden. Die Reihenfolge im Code ist bewusst egal,
# sortiert wird ausschließlich über get_customers().
CUSTOMERS: list[Customer] = [
    Customer(
        id="c1001",
        name="Anna Schneider",
        salutation="Frau Schneider",
        age=39,
        city="Bayreuth",
        housing="Eigentumswohnung",
        priority=1,
        category="prevention",
        urgency="Heute",
        topic_icon="umbrella",
        reason="Starkregenwarnung – Elementarschutz nicht hinterlegt",
        headline="Diese Woche kontaktieren",
        situation=[
            "Für Bayreuth besteht erhöhte Starkregengefahr.",
            "Ein Elementarschutz ist nicht hinterlegt.",
        ],
        recommendation="Schutzmaßnahmen erklären und Deckung gemeinsam prüfen.",
        benefit="Schaden verhindern",
        last_contact="12. Okt.",
        sources=["Wetterwarnung", "Wohnadresse", "Vertragsdaten"],
        explanation=[
            "Amtliche Wetterwarnung: Für Bayreuth ist ab heute Starkregen angekündigt.",
            "Wohnadresse: Die hinterlegte Adresse liegt im Warngebiet.",
            "Vertragsdaten: Hausrat und Haftpflicht sind vorhanden.",
            "Ein Elementarschutz wurde im Vertragsbestand nicht gefunden.",
        ],
        coverages=[
            Coverage(
                key="hausrat",
                label="Hausrat",
                icon="house",
                status="protected",
                contract={
                    "Vertragsnummer": "HR-204117 (synthetisch)",
                    "Versicherungssumme": "65.000 €",
                    "Selbstbeteiligung": "150 €",
                    "Vertragsbeginn": "03/2019",
                },
                recommendation="Kein Handlungsbedarf. Bei Gelegenheit Versicherungssumme bestätigen.",
                sources=["Vertragsdaten"],
            ),
            Coverage(
                key="elementar",
                label="Elementar",
                icon="waves",
                status="check",
                contract={"Status": "Im Vertragsbestand nicht gefunden"},
                recommendation=(
                    "Auf akute Starkregengefahr hinweisen, Schutzmaßnahmen erklären "
                    "und Elementardeckung gemeinsam prüfen."
                ),
                sources=["Amtliche Wetterwarnung", "Wohnadresse und Geländedaten", "Vertragsdaten"],
                open_questions=["Ist ein Keller vorhanden und wie wird er genutzt?"],
                title="Elementarschutz",
                kpis=[
                    Kpi("Vertragsstatus", "Nicht enthalten", "file", "danger"),
                    Kpi("Aktuelle Risikolage", "Erhöht", "warning", "danger"),
                    Kpi("Handlungsbedarf", "Diese Woche", "calendar", "warning"),
                ],
                signals=[
                    Signal("Erhöhtes Starkregenrisiko", 0.86, ["Amtliche Wetterwarnung", "nächste 7 Tage"], "cloud_rain"),
                    Signal("Wohnlage durch Überflutung gefährdet", 0.72, ["Geländehöhe", "Gewässernähe", "Region"], "waves"),
                    Signal("Rückstau im Gebäude möglich", 0.64, ["Gebäudetyp", "Baujahr", "Wohnlage"], "house"),
                    Signal("Wasserschaden in Kellerräumen", 0.41, ["Gebäudetyp", "Kellernutzung unbekannt"], "building"),
                    Signal("Hohe Schadenhöhe bei Eigentum", 0.33, ["Wohnsituation", "Hausratwert"], "home"),
                    Signal("Vergleichbare Schäden in der Nachbarschaft", 0.24, ["Regionale Schadenstatistik"], "map_pin"),
                    Signal("Hagel in den nächsten 30 Tagen", 0.18, ["Saisonale Wetterdaten"], "umbrella"),
                ],
                reasons=[
                    Reason(
                        "cloud_rain", "Wetterdaten", "Starkregenwarnung aktiv",
                        "Amtliche Unwetterwarnung für den Landkreis Bayreuth: bis zu 40 l/m² "
                        "in 6 Stunden, gültig ab heute für die nächsten Tage.",
                    ),
                    Reason(
                        "map_pin", "Standortdaten", "Niedrige Geländelage",
                        "Die Wohnadresse liegt in einer Senke rund 300 m vom Roten Main entfernt. "
                        "Bei Starkregen sammelt sich dort häufig Oberflächenwasser.",
                    ),
                    Reason(
                        "file", "Vertragsdaten", "Kein Elementarschutz hinterlegt",
                        "Hausrat und Haftpflicht sind vorhanden. Ein Baustein für Elementarschäden "
                        "(Überschwemmung, Rückstau) wurde nicht gefunden.",
                        show_contract=True,
                    ),
                ],
                action_title="Kundin diese Woche kontaktieren",
                benefit="Schaden verhindern",
                action_category="prevention",
                action_icon="umbrella",
                consent=(
                    "Wetter- und Geländedaten sind öffentlich verfügbar. Die Wohnadresse stammt "
                    "aus dem Vertrag; Frau Schneider hat der Nutzung für Präventionshinweise zugestimmt."
                ),
            ),
            Coverage(
                key="haftpflicht",
                label="Haftpflicht",
                icon="shield",
                status="protected",
                contract={
                    "Vertragsnummer": "PH-881203 (synthetisch)",
                    "Tarif": "Single",
                    "Deckungssumme": "10 Mio. €",
                },
                recommendation="Der Vertrag passt zur aktuellen Situation. Beim nächsten Jahresgespräch kurz bestätigen.",
                sources=["Vertragsdaten"],
            ),
        ],
        events=[
            Event("Heute", "Starkregenwarnung", "umbrella", is_new=True),
            Event("Vor 3 Monaten", "Umzug bestätigt", "house"),
        ],
        conversation_opening=(
            "Guten Tag Frau Schneider, für Ihre Region ist aktuell Starkregen angekündigt. "
            "Ich möchte gerne kurz mit Ihnen prüfen, ob Ihr Zuhause ausreichend geschützt ist."
        ),
        conversation_questions=[
            "War Ihre Wohnung oder Ihr Keller schon einmal von Wasser betroffen?",
            "Haben Sie bereits Vorkehrungen getroffen, zum Beispiel eine Rückstausicherung?",
            "Darf ich Ihnen zeigen, wie ein Elementarschutz Ihre Hausratversicherung ergänzt?",
        ],
        conversation_goal=(
            "Frau Schneider kennt einfache Schutzmaßnahmen und entscheidet informiert, "
            "ob sie ihren Schutz um Elementarschäden ergänzen möchte."
        ),
    ),
    Customer(
        id="c1002",
        name="Thomas Becker",
        salutation="Herr Becker",
        age=52,
        city="Nürnberg",
        housing="Einfamilienhaus",
        priority=2,
        category="gap",
        urgency="Diese Woche",
        topic_icon="house",
        reason="Hausratwert vermutlich über Versicherungssumme",
        headline="Diese Woche kontaktieren",
        situation=[
            "Die Versicherungssumme der Hausrat wurde seit 2014 nicht angepasst.",
            "Nach einem Anbau liegt der Hausratwert vermutlich deutlich höher.",
        ],
        recommendation="Versicherungssumme gemeinsam prüfen und bei Bedarf anpassen.",
        benefit="Deckungslücke vermeiden",
        last_contact="3. Mai",
        sources=["Vertragsdaten", "Wohnfläche", "Gesprächsnotiz"],
        explanation=[
            "Vertragsdaten: Versicherungssumme 45.000 €, seit 2014 unverändert.",
            "Wohnfläche: 160 m² – üblich wären rund 104.000 € (650 € pro m²).",
            "Gesprächsnotiz vom Mai: Herr Becker hat einen Wintergarten-Anbau erwähnt.",
            "Bei einer zu niedrigen Summe wird im Schadenfall eventuell nur anteilig erstattet.",
        ],
        coverages=[
            Coverage(
                key="hausrat",
                label="Hausrat",
                icon="house",
                status="check",
                contract={
                    "Vertragsnummer": "HR-117450 (synthetisch)",
                    "Versicherungssumme": "45.000 €",
                    "Letzte Anpassung": "2014",
                    "Schutz vor Unterversicherung": "Nein",
                },
                recommendation=(
                    "Hausratwert gemeinsam schätzen und die Versicherungssumme an die "
                    "aktuelle Wohnfläche anpassen."
                ),
                sources=["Vertragsdaten", "Wohnfläche", "Gesprächsnotiz"],
                open_questions=[
                    "Wie groß ist die Wohnfläche nach dem Anbau genau?",
                    "Gab es größere Anschaffungen in den letzten Jahren?",
                ],
                kpis=[
                    Kpi("Vertragsstatus", "Summe veraltet", "file", "warning"),
                    Kpi("Aktuelle Risikolage", "Unterversichert", "warning", "warning"),
                    Kpi("Handlungsbedarf", "Diese Woche", "calendar", "warning"),
                ],
                signals=[
                    Signal("Hausratwert über Versicherungssumme", 0.78, ["Wohnfläche", "Vergleichswerte Region"], "house"),
                    Signal("Neue Einrichtung nach Anbau", 0.61, ["Gesprächsnotiz", "Wohnfläche"], "building"),
                    Signal("Einbruchrisiko in der Wohngegend", 0.27, ["Regionale Schadenstatistik"], "shield"),
                ],
                reasons=[
                    Reason(
                        "file", "Vertragsdaten", "Summe seit 2014 unverändert",
                        "Die Versicherungssumme von 45.000 € wurde seit Vertragsbeginn nicht angepasst.",
                        show_contract=True,
                    ),
                    Reason(
                        "home", "Wohnfläche", "160 m² – Richtwert rund 104.000 €",
                        "Üblich sind etwa 650 € Hausratwert pro Quadratmeter Wohnfläche.",
                    ),
                    Reason(
                        "message", "Gesprächsnotiz", "Wintergarten-Anbau erwähnt",
                        "Im Gespräch vom 3. Mai hat Herr Becker einen neuen Wintergarten erwähnt.",
                    ),
                ],
                action_title="Kunden diese Woche kontaktieren",
                benefit="Deckungslücke vermeiden",
                action_category="gap",
            ),
            Coverage(
                key="wohngebaeude",
                label="Wohngebäude",
                icon="building",
                status="protected",
                contract={
                    "Vertragsnummer": "WG-550918 (synthetisch)",
                    "Elementarschutz": "Eingeschlossen",
                },
                recommendation="Anbau beim Gebäudeversicherer melden lassen.",
                sources=["Vertragsdaten"],
                open_questions=["Wurde der Anbau bereits gemeldet?"],
            ),
            Coverage(
                key="haftpflicht",
                label="Haftpflicht",
                icon="shield",
                status="protected",
                contract={"Tarif": "Familie", "Deckungssumme": "15 Mio. €"},
                recommendation="Der Vertrag passt zur aktuellen Situation. Beim nächsten Jahresgespräch kurz bestätigen.",
                sources=["Vertragsdaten"],
            ),
        ],
        events=[
            Event("Vor 5 Monaten", "Wintergarten-Anbau erwähnt", "message", is_new=True),
            Event("2014", "Hausrat zuletzt angepasst", "file"),
        ],
        conversation_opening=(
            "Guten Tag Herr Becker, Ihr Zuhause hat sich in den letzten Jahren verändert. "
            "Ich möchte kurz mit Ihnen prüfen, ob Ihre Hausratversicherung noch zum heutigen Wert passt."
        ),
        conversation_questions=[
            "Wie nutzen Sie den neuen Wintergarten, und wie ist er eingerichtet?",
            "Haben Sie seit 2014 größere Anschaffungen gemacht, etwa Möbel oder Elektronik?",
            "Wäre es für Sie hilfreich, wenn die Versicherungssumme künftig automatisch passt?",
        ],
        conversation_goal=(
            "Herr Becker weiß, ob seine Versicherungssumme ausreicht, und kann sie bei Bedarf anpassen."
        ),
    ),
    Customer(
        id="c1003",
        name="Julia Wagner",
        salutation="Frau Wagner",
        age=31,
        city="Erlangen",
        housing="Mietwohnung",
        priority=3,
        category="cross_sell",
        urgency="Diese Woche",
        topic_icon="bike",
        reason="Neues E-Bike erkannt – Schutz prüfen",
        headline="In den nächsten Tagen ansprechen",
        situation=[
            "Eine Zahlung bei einem Fahrradhändler deutet auf ein neues E-Bike hin.",
            "Fahrraddiebstahl ist in der Hausrat bisher nicht eingeschlossen.",
        ],
        recommendation="Tatsächlichen Kauf bestätigen und Schutzbedarf gemeinsam prüfen.",
        benefit="Neuen Wertgegenstand passend absichern",
        last_contact="28. Aug.",
        sources=["Zahlungsdaten (mit Einwilligung)", "Vertragsdaten"],
        explanation=[
            "Zahlungsdaten: Zahlung über 2.800 € bei einem Fahrradhändler (mit Einwilligung ausgewertet).",
            "Der Kauf ist nicht bestätigt – bitte im Gespräch nachfragen.",
            "Vertragsdaten: Hausrat vorhanden, Fahrradbaustein nicht eingeschlossen.",
        ],
        coverages=[
            Coverage(
                key="hausrat",
                label="Hausrat",
                icon="house",
                status="protected",
                contract={"Vertragsnummer": "HR-330872 (synthetisch)", "Versicherungssumme": "40.000 €"},
                recommendation="Der Vertrag passt zur aktuellen Situation. Beim nächsten Jahresgespräch kurz bestätigen.",
                sources=["Vertragsdaten"],
            ),
            Coverage(
                key="fahrrad",
                label="Fahrrad",
                icon="bike",
                status="check",
                contract={"Status": "Nicht eingeschlossen"},
                recommendation="Kauf bestätigen lassen und Fahrradschutz für das E-Bike anbieten.",
                sources=["Zahlungsdaten (mit Einwilligung)", "Vertragsdaten"],
                open_questions=[
                    "Wurde tatsächlich ein E-Bike gekauft?",
                    "Wo wird das Rad abgestellt?",
                ],
                title="Fahrradschutz",
                kpis=[
                    Kpi("Vertragsstatus", "Nicht enthalten", "file", "warning"),
                    Kpi("Aktuelle Risikolage", "Mittel", "warning", "warning"),
                    Kpi("Handlungsbedarf", "Nächste Tage", "calendar", "info"),
                ],
                signals=[
                    Signal("Neues E-Bike gekauft", 0.81, ["Zahlungsdaten", "Händlerkategorie"], "bike"),
                    Signal("Diebstahlrisiko am Wohnort", 0.47, ["Regionale Statistik", "Abstellort unbekannt"], "map_pin"),
                    Signal("Tägliche Nutzung für den Arbeitsweg", 0.29, ["Zahlungsmuster"], "calendar"),
                ],
                reasons=[
                    Reason(
                        "file", "Zahlungsdaten", "Zahlung bei Fahrradhändler",
                        "Zahlung über 2.800 € bei einem Fahrradhändler. Der Kauf ist nicht bestätigt.",
                    ),
                    Reason(
                        "shield", "Vertragsdaten", "Fahrradbaustein nicht enthalten",
                        "In der Hausrat ist Fahrraddiebstahl unterwegs nicht mitversichert.",
                        show_contract=True,
                    ),
                ],
                action_title="Kundin in den nächsten Tagen ansprechen",
                benefit="Neuen Wertgegenstand absichern",
                action_category="cross_sell",
                consent="Frau Wagner hat der Auswertung ihrer Zahlungsdaten für Beratungshinweise zugestimmt.",
            ),
            Coverage(
                key="haftpflicht",
                label="Haftpflicht",
                icon="shield",
                status="protected",
                contract={"Tarif": "Single", "Deckungssumme": "10 Mio. €"},
                recommendation="Der Vertrag passt zur aktuellen Situation. Beim nächsten Jahresgespräch kurz bestätigen.",
                sources=["Vertragsdaten"],
            ),
        ],
        events=[
            Event("Vor 1 Woche", "Zahlung bei Fahrradhändler", "bike", is_new=True),
            Event("Vor 1 Jahr", "Hausrat abgeschlossen", "file"),
        ],
        conversation_opening=(
            "Hallo Frau Wagner, ich möchte sicherstellen, dass Ihre Versicherung zu Ihrem Alltag passt. "
            "Haben Sie sich kürzlich ein neues Fahrrad angeschafft?"
        ),
        conversation_questions=[
            "Nutzen Sie das E-Bike täglich, zum Beispiel für den Weg zur Arbeit?",
            "Wo steht das Rad nachts – im Keller, im Hof oder auf der Straße?",
            "Möchten Sie das E-Bike auch unterwegs gegen Diebstahl absichern?",
        ],
        conversation_goal=(
            "Frau Wagner weiß, ob ihr E-Bike geschützt ist, und kann den passenden Schutz wählen."
        ),
    ),
    Customer(
        id="c1004",
        name="Lena Fischer",
        salutation="Frau Fischer",
        age=34,
        city="Bamberg",
        housing="Mietwohnung",
        priority=4,
        category="cross_sell",
        urgency="Diese Woche",
        topic_icon="heart",
        reason="Nachwuchs angekündigt – Familienschutz prüfen",
        headline="In den nächsten Tagen ansprechen",
        situation=[
            "Frau Fischer hat im letzten Gespräch Nachwuchs angekündigt.",
            "Die Haftpflicht ist bisher als Single-Tarif abgeschlossen.",
        ],
        recommendation="Haftpflicht auf Familientarif umstellen und Absicherung der Familie besprechen.",
        benefit="Familie von Anfang an absichern",
        last_contact="2. Sep.",
        sources=["Gesprächsnotiz", "Vertragsdaten"],
        explanation=[
            "Gesprächsnotiz vom September: Nachwuchs für Anfang nächsten Jahres erwartet.",
            "Vertragsdaten: Haftpflicht im Single-Tarif, keine Unfallversicherung.",
        ],
        coverages=[
            Coverage(
                key="hausrat",
                label="Hausrat",
                icon="house",
                status="protected",
                contract={"Versicherungssumme": "35.000 €"},
                recommendation="Der Vertrag passt zur aktuellen Situation. Beim nächsten Jahresgespräch kurz bestätigen.",
                sources=["Vertragsdaten"],
            ),
            Coverage(
                key="haftpflicht",
                label="Haftpflicht",
                icon="shield",
                status="check",
                contract={"Tarif": "Single", "Deckungssumme": "10 Mio. €"},
                recommendation="Auf Familientarif umstellen, damit Partner und Kind mitversichert sind.",
                sources=["Gesprächsnotiz", "Vertragsdaten"],
                open_questions=["Lebt der Partner bereits im gemeinsamen Haushalt?"],
                title="Privathaftpflicht",
                kpis=[
                    Kpi("Vertragsstatus", "Single-Tarif", "file", "warning"),
                    Kpi("Aktuelle Risikolage", "Steigt mit Familie", "warning", "warning"),
                    Kpi("Handlungsbedarf", "Nächste Tage", "calendar", "info"),
                ],
                signals=[
                    Signal("Familienzuwachs in den nächsten Monaten", 0.90, ["Gesprächsnotiz"], "heart"),
                    Signal("Partner im gemeinsamen Haushalt", 0.55, ["Meldeadresse", "Gesprächsnotiz"], "users"),
                ],
                reasons=[
                    Reason(
                        "message", "Gesprächsnotiz", "Nachwuchs angekündigt",
                        "Im Gespräch vom 2. September hat Frau Fischer Nachwuchs für Anfang nächsten Jahres erwähnt.",
                    ),
                    Reason(
                        "file", "Vertragsdaten", "Single-Tarif ohne Familie",
                        "Kinder und Partner sind im Single-Tarif nicht mitversichert.",
                        show_contract=True,
                    ),
                ],
                action_title="Kundin in den nächsten Tagen ansprechen",
                benefit="Familie von Anfang an absichern",
                action_category="cross_sell",
            ),
            Coverage(
                key="unfall",
                label="Unfall",
                icon="heart",
                status="missing",
                recommendation="Kinderunfallschutz im Gespräch kurz vorstellen.",
                sources=["Vertragsdaten"],
            ),
        ],
        events=[
            Event("Vor 7 Wochen", "Nachwuchs im Gespräch erwähnt", "message", is_new=True),
            Event("Vor 2 Jahren", "Haftpflicht abgeschlossen", "file"),
        ],
        conversation_opening=(
            "Guten Tag Frau Fischer, herzlichen Glückwunsch zum erwarteten Nachwuchs! "
            "Ich möchte kurz mit Ihnen schauen, ob Ihre Familie gut abgesichert ist."
        ),
        conversation_questions=[
            "Wohnen Sie bereits mit Ihrem Partner zusammen?",
            "Wissen Sie, dass Ihr Kind in der Single-Haftpflicht nicht mitversichert ist?",
            "Möchten Sie auch über einen Unfallschutz für Ihr Kind sprechen?",
        ],
        conversation_goal="Frau Fischer weiß, welche Verträge sie für die Familie anpassen sollte.",
    ),
    Customer(
        id="c1005",
        name="Max Hoffmann",
        salutation="Herr Hoffmann",
        age=63,
        city="Bayreuth",
        housing="Einfamilienhaus",
        priority=5,
        category="cross_sell",
        urgency="Diese Woche",
        topic_icon="calendar",
        reason="Ruhestand in Kürze – Absicherung anpassen",
        headline="In den nächsten Tagen ansprechen",
        situation=[
            "Herr Hoffmann geht in vier Monaten in den Ruhestand.",
            "Sein Unfallschutz über den Arbeitgeber endet dann.",
        ],
        recommendation="Absicherung für den Ruhestand gemeinsam durchgehen.",
        benefit="Gut abgesichert in den Ruhestand",
        last_contact="15. Jun.",
        sources=["Gesprächsnotiz", "Vertragsdaten"],
        explanation=[
            "Gesprächsnotiz vom Juni: Renteneintritt zum 1. März geplant.",
            "Vertragsdaten: Unfallschutz läuft über eine Gruppenversicherung des Arbeitgebers.",
        ],
        coverages=[
            Coverage(
                key="wohngebaeude",
                label="Wohngebäude",
                icon="building",
                status="protected",
                contract={"Elementarschutz": "Eingeschlossen"},
                recommendation="Der Vertrag passt zur aktuellen Situation. Beim nächsten Jahresgespräch kurz bestätigen.",
                sources=["Vertragsdaten"],
            ),
            Coverage(
                key="haftpflicht",
                label="Haftpflicht",
                icon="shield",
                status="protected",
                contract={"Tarif": "Paar"},
                recommendation="Der Vertrag passt zur aktuellen Situation. Beim nächsten Jahresgespräch kurz bestätigen.",
                sources=["Vertragsdaten"],
            ),
            Coverage(
                key="unfall",
                label="Unfall",
                icon="heart",
                status="check",
                contract={"Status": "Über Arbeitgeber, endet mit Ruhestand"},
                recommendation="Private Unfallversicherung für die Zeit nach dem Berufsleben vorstellen.",
                sources=["Gesprächsnotiz", "Vertragsdaten"],
                open_questions=["Steht das Datum des Renteneintritts fest?"],
                title="Unfallschutz",
                kpis=[
                    Kpi("Vertragsstatus", "Endet in 4 Monaten", "file", "warning"),
                    Kpi("Aktuelle Risikolage", "Normal", "shield", "ok"),
                    Kpi("Handlungsbedarf", "Nächste Tage", "calendar", "info"),
                ],
                signals=[
                    Signal("Unfallschutz endet mit dem Ruhestand", 0.95, ["Vertragsdaten Arbeitgeber"], "calendar"),
                    Signal("Mehr Freizeitaktivität im Ruhestand", 0.38, ["Altersgruppe", "Gesprächsnotiz"], "bike"),
                ],
                reasons=[
                    Reason(
                        "message", "Gesprächsnotiz", "Renteneintritt zum 1. März",
                        "Im Gespräch vom 15. Juni hat Herr Hoffmann seinen geplanten Renteneintritt genannt.",
                    ),
                    Reason(
                        "file", "Vertragsdaten", "Schutz über den Arbeitgeber",
                        "Der Unfallschutz läuft über eine Gruppenversicherung und endet mit dem Arbeitsverhältnis.",
                        show_contract=True,
                    ),
                ],
                action_title="Kunden in den nächsten Tagen ansprechen",
                benefit="Gut abgesichert in den Ruhestand",
                action_category="cross_sell",
            ),
        ],
        events=[
            Event("In 4 Monaten", "Ruhestand", "calendar", is_new=True),
            Event("Vor 4 Monaten", "Gespräch zur Altersvorsorge", "message"),
        ],
        conversation_opening=(
            "Guten Tag Herr Hoffmann, Ihr Ruhestand rückt näher. Ich möchte mit Ihnen kurz schauen, "
            "welche Absicherungen sich dadurch verändern."
        ),
        conversation_questions=[
            "Steht der Termin für Ihren Renteneintritt schon fest?",
            "Wissen Sie, dass Ihr Unfallschutz über den Arbeitgeber dann endet?",
            "Welche Pläne haben Sie für die Zeit nach dem Berufsleben?",
        ],
        conversation_goal="Herr Hoffmann weiß, welche Verträge er vor dem Ruhestand anpassen sollte.",
    ),
]


# ============================================================
# Zugriffsfunktionen
# ============================================================

# Liefert die Kunden in fachlicher Reihenfolge. Zuerst entscheidet die Kategorie
# (Prävention vor Deckungslücke vor Cross-Sell), danach die vergebene Priorität.
# Später kann hier die Liste aus dem Digital Twin bzw. einem Modell geladen werden.
def get_customers() -> list[Customer]:
    """Gibt alle Kunden sortiert nach Kategorie-Rangfolge und Priorität zurück."""
    return sorted(CUSTOMERS, key=lambda c: (CATEGORIES[c.category].order, c.priority))


# Sucht einen einzelnen Kunden anhand seiner ID, z. B. für die Detailansicht.
def get_customer(customer_id: str) -> Customer | None:
    """Gibt den Kunden mit der angegebenen ID zurück oder None, falls unbekannt."""
    return next((c for c in CUSTOMERS if c.id == customer_id), None)
