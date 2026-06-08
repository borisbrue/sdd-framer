---
id: CON-0147
project: ''
title: Hub Projekt-Status & Steuerungs-API
type: api
format: openapi
spec: SPEC-0040
version: 0.1.0
status: draft
artifact: contracts/api/hub-projekt-status-steuerungs-api.openapi.yaml
tests:
- TST-0170
- TST-0174
---
Dieser Contract definiert die HTTP-REST-Schnittstelle zwischen der PWA und dem Hub-Dienst für den Abruf von Projektstatus-Informationen sowie die Steuerung von Projektservern.

**Zweck**

Die PWA nutzt diese API lesend (Projektstatus) und steuernd (Start/Stopp-Aktionen). Ein dedizierter Heartbeat-Endpunkt ermöglicht der PWA, die Hub-Erreichbarkeit aktiv zu überwachen und selbstständig zwischen Online- und Offline-Modus zu wechseln (FR-08).

**Garantien des Hub-Dienstes**

- `GET /projects` liefert immer die vollständige Liste aller registrierten Projekte mit aktuellem Status; Antwortzeit ≤ 2 Sekunden (FR-01).
- `POST /projects/{projectId}/start` und `POST /projects/{projectId}/stop` geben eine `202 Accepted`-Antwort zurück; die sichtbare Statusänderung ist innerhalb von ≤ 5 Sekunden über `GET /projects/{projectId}` abrufbar (FR-03, FR-04, FR-07).
- `GET /health` antwortet immer mit `200` oder `503`, solange der Hub-Prozess läuft (FR-08).
- Der Serverstatus eines Projekts ist stets einer der Werte: `running`, `stopped`, `starting`, `stopping`, `error` (FR-02).
- Fehler werden einheitlich als `Error`-Objekt mit `code` und `message` zurückgegeben.
- Start/Stopp-Aktionen werden mit `409 Conflict` abgelehnt, wenn das Projekt nicht im erwarteten Ausgangsstatus ist (FR-05).
- `ProjectList.retrievedAt` gibt den genauen Abrufzeitpunkt an, den die PWA für den Offline-Hinweis mit Zeitstempel verwendet (FR-06).

**Geltungsbereich**

Abgedeckt: Projektstatus lesen (`GET /projects`, `GET /projects/{projectId}`), Projektserver starten (`POST /projects/{projectId}/start`), stoppen (`POST /projects/{projectId}/stop`), Hub-Erreichbarkeit prüfen (`GET /health`).

Nicht abgedeckt: Projekte anlegen, konfigurieren oder löschen; Logs und Metriken; Nutzer- und Rollenverwaltung; Hub-Systemkonfiguration; Offline-Steuerung ohne aktive Hub-Verbindung.

**Konsument**

Primärer Konsument ist die SDD-Framer-PWA. Die API ist zustandslos; Authentifizierung erfolgt über den im Hub konfigurierten Mechanismus (nicht Teil dieses Contracts).