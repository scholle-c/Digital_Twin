# Demo-Drehbuch Berater-Dashboard: Anna

Berater: **Markus**, Kundenberater. Kundin: **Anna Schneider** (C0021), 27, Studentin, Single, Erlangen.
Ihr Signal: Fahrraddiebstahl am 15.07.2026, 3.200 €, Anspruch abgelehnt, weil die Hausrat keinen
Fahrradbaustein hat. Genau der Fall, den Rene als Retention-Signal beschrieben hat. Dauer: etwa 4 Minuten.

Vorbereitung:
- Dashboard starten (`dashboard/`), Portal optional daneben
- `.env` mit `ANTHROPIC_API_KEY` im Projektordner, sonst erscheint statt des KI-Berichts der regelbasierte Leitfaden
- Beim ersten Öffnen rechnet das Dashboard alle Twins (Spinner, wenige Sekunden)

| # | Klick | Was man sieht | Was man sagt |
|---|---|---|---|
| 1 | Dashboard öffnen | "Guten Morgen, Markus", priorisierte Liste, Anna Schneider auf Platz 1 in Lila, Kategorie KUNDENBINDUNG, "Diese Woche" | "Markus bekommt keine Kundenliste, sondern eine Reihenfolge: wen muss ich diese Woche anrufen und warum. Ganz oben: Anna." |
| 2 | Auf die Karte zeigen | Begründung in der Karte: "Fahrraddiebstahl am 15.07.2026 über 3200 € abgelehnt: Entscheidung erklären, Alternative anbieten, Kündigungsrisiko senken" | "Kein Vertrieb, sondern Kundenbindung. Ein abgelehnter Schaden ist der häufigste Grund für eine Kündigung. Der Twin hat das erkannt, bevor Anna kündigt." |
| 3 | Rechts: Kopf der Detailansicht | "Letzter Kontakt: Schadenmeldung 15.07.2026", Quellen: Kundendaten, Gebäudedaten, Life Events, Schadenhistorie | "Alle Quellen auf einen Blick. 'Warum sehe ich das?' erklärt die Datenbasis." |
| 4 | **Das Wichtigste jetzt** | Zwei Sätze: abgelehnter Schaden nachfassen, Fahrradbaustein schließt die Lücke. Kundennutzen: Vertrauen erhalten | "Das Gespräch hat zwei Teile: zuerst erklären, dann eine Lösung anbieten. In dieser Reihenfolge." |
| 5 | **Handlungsempfehlung aus dem Digital Twin** | Kundenbindung sichern, diese Woche, Konfidenz 90 %, Belege: Schadenfall, Autokauf, Einbruchtrend Bayern, ähnliche Kunden. Weitere offene Punkte: Fahrradbaustein, Einbruchschutz, Hausrat-Summe | "Jede Empfehlung kommt mit Belegen und einer Konfidenz. 90 %, weil ein abgelehnter Schaden ein Fakt ist, keine Prognose." |
| 6 | **Gespräch vorbereiten** | Nach etwa 10 Sekunden der KI-Kurzbericht: Situation, nächste Aktion, Gesprächseinstieg wörtlich, drei Fragen, Belege, "Nicht ansprechen" | "Claude fasst den Twin-Kontext in einen Gesprächsleitfaden. Markus liest zwei Minuten und ruft an. Die Entscheidung bleibt bei ihm." |
| 7 | Sidebar-Chat: "Warum wurde Annas Anspruch abgelehnt und was biete ich ihr an?" | Antwort aus dem Kontext: kein Fahrradbaustein, Fahrradbaustein anbieten, Hausrat-Summe prüfen | "Rückfragen gehen direkt an den Twin, ohne Aktensuche." |
| 8 | Reiter **Digital Twin** | Position im Bestand, ähnlichste Twins, regionale Heatmap mit Zeitschieber für Bayern | "Anna im Vergleich zu 47 anderen Kunden, und ihre Region über die Zeit. Der Einbruchtrend in Bayern steigt, das fließt in die Empfehlung ein." |
| 9 | Zurück zur Liste, Platz 2 bis 5 zeigen | Jonas Fischer: Kind geboren, Familienhaftpflicht. Tim Schmidt: kein Rauchmelder, Altbau | "Dieselbe Logik für jeden Kunden: Kundenbindung vor Prävention vor Lücke vor Cross-Sell, frische Signale zuerst." |

Übergang zur Portal-Demo, falls beide gezeigt werden: Erst Portal (Anna meldet Umzug), dann Dashboard neu laden.
Anna hat dann zwei Signale, abgelehnter Schaden und Umzug, und steht erst recht oben.

Sätze für die Jury:
- "Woher kommt die Priorisierung?" Regeln in `config.toml`, jede mit Bedingung und Text. Kein Modell entscheidet, Modelle liefern Signale (Risikoscore, Ähnlichkeit, regionaler Trend).
- "Was macht die KI?" Zusammenfassen und formulieren. Zahlen und Entscheidung kommen aus dem Twin.
- "Was ist neu gegenüber Customer 360?" Customer 360 zeigt, was ist. Der Twin sagt, was jetzt zählt und was zu tun ist, mit Belegen.
