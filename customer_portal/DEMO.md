# Demo-Drehbuch Kundenportal: Anna

Persona: **Anna Schneider**, 27, Studentin, Single, wohnt in Erlangen. Sie sucht eine Beziehung und
überlegt umzuziehen. Login: Kunden-ID `C0021`, Passwort `demo`. Dauer: etwa 5 Minuten.

Vorbereitung:
- Portal starten (`customer_portal/`), Dashboard starten (`dashboard/`), beide im Browser offen
- `generated_demodata/` sauber: `git checkout generated_demodata/` und `portal_profiles.csv` löschen
- Nach der Demo wieder zurücksetzen (gleicher Befehl)

| # | Klick | Was man sieht | Was man sagt |
|---|---|---|---|
| 1 | Login mit `C0021` / `demo` | Startseite "Guten Morgen, Anna!", 67 % abgesichert, 3 Verträge, 60,80 € im Monat | "Anna ist Studentin, hat Hausrat, Haftpflicht und seit dem Autokauf im März eine Kfz-Police. Ihr Digital Twin kennt ihre Lebenslage." |
| 2 | Auf der Startseite unten rechts: Kachel **Meine Region** zeigt "Sichere Gegend · 52 % Singles · viele in Ihrem Alter" | Teaser | "Der Twin kennt nicht nur Anna, sondern auch ihre Umgebung." |
| 3 | Kachel **Meine Region öffnen** | Trends & Analysen, oben die Karten: Ihre Gegend ist sicher, Viele Singles, Viele in Ihrem Alter, Interessen, Naturereignisse | "Das sind anonymisierte Kundenprofile und Vorfalldaten aus Annas Umfeld. Sie erfährt: hier ist es sicher, und hier leben viele Singles in ihrem Alter. Für jemanden, der eine Beziehung sucht, ist das ein Argument zu bleiben." |
| 4 | **Anderen Ort prüfen**, "München" eintippen | Vergleichstabelle Erlangen vs. München, Fazit "weniger sicher, viele Singles", Karte springt nach München | "Anna überlegt trotzdem umzuziehen. Sie prüft München: mehr Singles in absoluten Zahlen, aber 5 % mehr Einbrüche und weniger Leute in ihrem Alter." |
| 5 | Optional: "Bayreuth" oder "Berlin" eintippen | Bayreuth: sicher, ruhig. Berlin: 35 % mehr Einbrüche, 55 % Singles | "Jeder Ort hat sein Profil. Der Twin sagt Anna, was sich für ihren Schutz ändert, bevor sie den Mietvertrag unterschreibt." |
| 6 | Button **Umzug nach München melden** | Profilseite öffnet sich, Formular mit Umzug, PLZ 80331, München, Bayern vorausgefüllt | "Anna entscheidet sich. Ein Klick, und das Ereignis ist im Formular." |
| 7 | **Speichern** | Toast "Umzug gespeichert", Mitteilung, Adresse im Profil ist München | "Der Umzug steht jetzt in den Kundendaten, nicht nur in der App. Das ist die Source of Truth, auch für den Berater." |
| 8 | **Übersicht** | Nächste Schritte: "Umzugs-Check" ganz oben, Risiken neu berechnet | "Der Twin hat sofort reagiert: Versicherungssumme, Gefährdungszone und Elementarschutz für die neue Adresse prüfen." |
| 9 | Wechsel ins **Berater-Dashboard**, Seite neu laden | Anna Schneider auf Platz 1 der priorisierten Kunden, Handlungsempfehlung "Umzugs-Check", Belege: Life Event Umzug | "Und das sieht der Berater: Anna steht oben, mit Begründung und Konfidenz, ohne dass jemand anrufen musste." |
| 10 | **Gespräch vorbereiten** | KI-Kurzbericht in 10 Sekunden: Situation, nächste Aktion, Gesprächseinstieg, drei Fragen, Belege | "Claude fasst den Twin-Kontext zusammen. Entscheidung bleibt beim Berater." |

Sätze für die Jury, wenn Fragen kommen:
- "Woher kommen die Regionsdaten?" Aus anonymisierten Kundenprofilen der Umgebung plus Vorfall- und Naturgefahrendaten. Bei kleinen Stichproben greift ein Regionsprofil, das steht unter der Überschrift.
- "Ist das Datenschutz-konform?" Nur Aggregate, nie Einzelpersonen. Anna sieht "52 % Singles", nie wer.
- "Was ist daran neu?" Der Twin verbindet Person, Haushalt, Region und Zeit. Ein Umzug ist nicht nur eine Adressänderung, sondern ein neues Risikoprofil, das der Berater sofort sieht.

Reserve, falls Zeit bleibt: Chat in der Dashboard-Sidebar: "Warum steht Anna auf Platz 1?"
