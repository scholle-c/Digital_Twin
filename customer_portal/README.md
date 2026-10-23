# Allianz Digital Twin – Kundenportal (Prototyp)

Responsives Kundenportal in Streamlit: Login, Dashboard mit Absicherungsgrad, Vertragsübersicht,
Profilverwaltung, Fragebogen, Trends & Heatmap sowie individuelle Angebote.
Alle Kunden-, Vertrags- und Risikodaten sind **fiktiv** und als Prototyp gekennzeichnet.

## Start

Voraussetzung: Python 3.11+ (der Digital Twin nutzt `tomllib`).

```powershell
cd customer_portal
uv run --python 3.12 --with-requirements requirements.txt streamlit run app.py
```

oder mit eigener Umgebung:

```powershell
cd customer_portal
uv venv --python 3.12
uv pip install -r requirements.txt
uv run streamlit run app.py
```

Wichtig: im Ordner `customer_portal/` starten, damit `.streamlit/config.toml` (helles Design) greift.

**Demo-Zugang:** Kundennummer `DT-100010` oder `max.bauer@example.com`, Passwort `demo`.
Es gibt keine echte Authentifizierung – bitte keine echten Zugangsdaten eingeben.

## Seiten

| Seite | Inhalt |
|---|---|
| Login | Demo-Anmeldung, Passwort vergessen, Registrierung mit Validierung, biometrischer Login (Konzept) |
| Übersicht | Absicherungsgrad (Ring), Versicherungsstatus, nächste Schritte, Verträge, Mitteilungen, Risiken, Schnellzugriff |
| Meine Versicherungen | Kennzahlen, Statusfilter, Vertragskarten mit Detailansicht und Prüfhinweisen |
| Mein Profil | Persönliche Daten (geschützt), Haushalt & Lebenssituation, Präferenzen – jeweils Bearbeiten/Speichern mit Validierung |
| Umfragen | 4 Schritte + Prüfseite, Fortschrittsanzeige, bedingte Fragen, Zwischenspeichern, Absenden |
| Trends & Analysen | Filter (Region, Zeitraum, Kategorie), Kennzahlen mit Tooltips, Heatmap, Trenddiagramm, Demografie, persönliches Risikoprofil |
| Angebote | Begründete Empfehlungen mit Quelle, Leistungen und Beispielpreis; ansehen, anfragen, ausblenden |
| Mitteilungen / Einstellungen | Gelesen-Status, Einwilligungen (DSGVO), Benachrichtigungen, Demo zurücksetzen |

Desktop: Sidebar links, Kopfleiste mit Suche. Mobil (≤ 768 px): kompakte Kopfzeile, Navigationsleiste unten,
Karten untereinander, kein horizontales Scrollen.

## Wie die Personalisierung funktioniert

1. **Digital Twin** (`../digital_twin.py`, `../config.toml`): Das Portal übergibt Kunde C0010 aus
   `../generated_demodata`, die aktiven Verträge und die Rauchmelder-Angabe aus dem Fragebogen.
   Zurück kommen Risiken, Lebensereignis-Prognosen und Empfehlungen.
2. **Eigene Regeln** (`core/personalization.py`): ergänzen Angebote aus Profil und Fragebogen
   (z. B. Wohngebäude bei Eigentum, Reiseversicherung bei Priorität „Reisen“).
3. **Absicherungsgrad**: gewichtete Bedarfsfelder; welche Felder relevant sind, hängt von Profil und Antworten ab.

Ändert sich Profil oder Fragebogen, rechnen Dashboard und Angebote beim nächsten Klick neu.
Beispiel: „Rauchmelder in allen Räumen“ im Fragebogen → der Twin empfiehlt keinen Rauchmelder-Check mehr.

## Aufbau

```
customer_portal/
├── app.py                    Einstieg: Login-Gate, Kontext, Routing
├── core/
│   ├── data.py               Demodaten, Verträge, CSV-Loader, Mitteilungen
│   ├── twin.py               Anbindung an den Digital Twin des Projekts
│   ├── personalization.py    Absicherungsgrad, Angebotskatalog, Regeln
│   └── state.py              Sitzungszustand und alle Aktionen (Callbacks)
├── ui/
│   ├── components.py         Designsystem: Badges, Kacheln, Ring, Leerzustände
│   └── layout.py             Sidebar, Kopfleiste, Suche, mobile Navigation
├── views/                    eine Datei pro Seite
├── styles/portal.css         Design-Tokens, Komponenten, Responsive-Regeln
└── .streamlit/config.toml    helles Theme
```

## Erweitern

- **Echtes Backend:** nur `core/state.py` (Login, Speichern) und `core/data.py` (Verträge, Profil) austauschen.
- **Echte Analysedaten:** Loader in `core/data.py` ersetzen; `views/trends.py` erwartet dieselben Spalten.
- **Neue Frage:** einen `Question(...)`-Eintrag in `STEPS` (`views/questionnaire.py`) ergänzen.
- **Neues Produkt:** Eintrag in `CATALOG` und eine Regel in `build_offers()` (`core/personalization.py`).
- **Logo:** Die Wortmarke steht in `logo_html()` (`ui/components.py`). Das offizielle Allianz-Logo ist
  markenrechtlich geschützt und nur mit Freigabe zu verwenden.

## Hinweise

- Preise und Leistungen sind Beispielwerte, keine echten Tarife oder verbindliche Deckungsauskünfte.
- Trend- und Heatmap-Daten sind synthetisch und keine offiziellen Allianz-Daten.
- Die Heatmap lädt die Kartengrundlage von Carto (Internet nötig); ohne Internet erscheinen nur die Datenpunkte.
- Alle Eingaben leben in der Browsersitzung (`st.session_state`) und gehen beim Neuladen verloren.
