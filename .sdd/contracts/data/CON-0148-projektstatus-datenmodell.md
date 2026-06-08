---
id: CON-0148
project: ''
title: Projektstatus-Datenmodell
type: data
format: json-schema
spec: SPEC-0040
version: 0.1.0
status: draft
artifact: contracts/data/projektstatus-datenmodell.schema.json
tests:
- TST-0171
---
Dieser Contract definiert das Datenmodell für Projektstatus-Antworten der Hub-API. Er ist verbindlich für alle Endpunkte, die eine Liste hinterlegter Projekte mit ihrem jeweiligen Serverstatus an die PWA ausliefern.

**Zweck**

Hub und PWA verwenden dieses Schema als gemeinsame Schnittstellenvereinbarung. Es legt fest, welche Felder die PWA beim Abruf von Projektlisten erwarten, validieren und auswerten darf. Das Schema ist die Grundlage für die Darstellung der Projektliste (FR-02), den initialen Statusabruf (FR-01) sowie die Offline-Anzeige mit dem zuletzt bekannten Zustand (FR-06).

**Garantien**

- Jedes Projektobjekt enthält mindestens eine eindeutige maschinenlesbare ID, einen menschenlesbaren Anzeigenamen und einen normierten Serverstatus.
- Der Serverstatus ist ausschließlich auf die vier Werte `running`, `stopped`, `starting` und `stopping` beschränkt; kein anderer Wert ist zulässig.
- Die Wurzelantwort enthält immer einen ISO-8601-Zeitstempel des Abrufs (`fetchedAt`) sowie den aktuellen Hub-Verbindungsstatus (`hubConnection`).
- Optionale Felder (`statusChangedAt`) können fehlen; die PWA muss ihre Abwesenheit tolerieren, ohne in einen Fehlerzustand zu wechseln.
- Bei Verbindungsverlust bleibt das zuletzt empfangene, gegen dieses Schema validierte Objekt der einzig zulässige angezeigte Zustand (kein leerer oder ungültiger Zustand).

**Geltungsbereich**

Dieses Schema gilt für:
- `GET /projects` — vollständige Projektliste mit Statusangaben
- Jede weitere Antwort, die von der PWA zur Darstellung der Projektliste ausgewertet wird

Ausdrücklich nicht abgedeckt:
- Aktions-Endpunkte für Start/Stopp (eigene Contracts)
- Detailansichten einzelner Projekte mit Logs oder Metriken
- Verwaltungsoperationen (Anlegen, Konfigurieren, Löschen von Projekten)