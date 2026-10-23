# Customer 360 – Beratungscockpit (Streamlit-Prototyp)

Klickbarer Prototyp für Versicherungsberater: priorisierte Kundenliste, Kundendetail mit
wichtigster Empfehlung, Begründung („Warum sehe ich das?“), Gesprächsvorbereitung,
aktueller Absicherung und Ereignis-Timeline. Alle Daten sind **synthetisch**.

Fachliche Reihenfolge: **1. Prävention → 2. Deckungslücke → 3. Cross-Sell** (Fürsorge vor Vertrieb).

## Installation

Voraussetzung: Python 3.10–3.13.

```bash
cd dashboard
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

## Start

```bash
cd dashboard
streamlit run app.py
```

Die App öffnet sich unter <http://localhost:8501>. Wichtig: im Ordner `dashboard/` starten,
damit `.streamlit/config.toml` (helles Design) geladen wird.

Alternativ mit [uv](https://docs.astral.sh/uv/):
`uv run --python 3.12 --with-requirements requirements.txt streamlit run app.py`

## Aufbau

| Datei | Inhalt |
|---|---|
| `app.py` | Einstiegspunkt: Seitenkonfiguration, Laden von CSS/Daten, Layout |
| `state.py` | `st.session_state` und Klick-Callbacks (Kunde, Versicherung, Gesprächsvorbereitung) |
| `data/mock_data.py` | Datenmodell (Dataclasses) und synthetische Kunden |
| `components/layout.py` | CSS-Einbindung, linke Navigation, Kopfbereich |
| `components/customer_list.py` | Priorisierte, klickbare Kundenkarten |
| `components/customer_detail.py` | Profil, Empfehlung, Gesprächsvorbereitung, Absicherung, Timeline |
| `components/coverage_detail.py` | Versicherungsdetailseite: Kennzahlen, Content Enrichment, Begründung, offene Informationen, Handlungsempfehlung |
| `components/ui.py` | Symbole (Inline-SVG), HTML-Ausgabe, Statusanzeige |
| `i18n.py` | Sprachumschaltung Deutsch/Englisch: `t()` für Oberflächentexte, `tr()` für Datentexte |
| `data/translations_en.py` | Englische Übersetzungen der Mockdaten (Deutsch bleibt die Quelle) |
| `styles/dashboard.css` | Design-Tokens und gesamtes Styling |
| `.streamlit/config.toml` | Erzwingt das helle Theme |

## Sprache

Der Button unter der linken Navigation schaltet zwischen Deutsch und Englisch um; Auswahl und
geöffnete Seite bleiben dabei erhalten.

- **Neuer Oberflächentext:** Eintrag in `UI_TEXT` in `i18n.py` anlegen und mit `t("schlüssel")` verwenden.
- **Neuer Datentext:** deutschen Text wie gewohnt in `mock_data.py` schreiben und die englische Fassung in
  `data/translations_en.py` ergänzen. Alles, was über `esc()` ausgegeben wird, wird automatisch übersetzt.
  Fehlt eine Übersetzung, erscheint der deutsche Text.

## Erweiterung

- **Echte Daten / Digital Twin:** `get_customers()` in `data/mock_data.py` ersetzen, z. B. durch
  eine Umwandlung von `DigitalTwin.recommendations()` aus `../interface.py` in `Customer`-Objekte.
  Die Kategorien heißen bereits gleich (`prevention`, `gap`, `cross_sell`).
- **Content Enrichment / Wahrscheinlichkeiten:** `Coverage.signals` mit `Signal(titel, wahrscheinlichkeit, merkmale, symbol)`
  befüllen. Die Detailseite sortiert nach Wahrscheinlichkeit, zeigt die drei wichtigsten und klappt den Rest auf.
  Farbe: ab 80 % rot, ab 50 % orange, darunter blau. Wahrscheinlichkeiten erscheinen bewusst nur auf der Detailseite.
- **Begründungen:** `Coverage.reasons` (`Reason`) – aufklappbar unter „Warum diese Einschätzung?“.
- **Kennzahlen und Empfehlung:** `Coverage.kpis`, `action_title`, `recommendation`, `benefit`, `action_category`.
  Fehlen sie, setzt `Coverage.__post_init__` passende Standardwerte je Status.
- **Weitere Kunden:** zusätzlichen `Customer(...)` in `CUSTOMERS` anlegen – Liste, Zähler im Kopfbereich
  und Detailansicht passen sich automatisch an.
- **Versicherungsdetailseite:** `render_coverage_detail()` in `components/customer_detail.py` ist der
  Andockpunkt (später z. B. als eigene Seite über `st.navigation`).
