---
id: CON-0149
project: ''
title: Hub-Verbindungs-Health-Endpunkt
type: api
format: openapi
spec: SPEC-0040
version: 0.1.0
status: draft
artifact: contracts/api/hub-verbindungs-health-endpunkt.openapi.yaml
tests:
- TST-0172
- TST-0176
- TST-0177
---
Dieser Contract beschreibt die HTTP-Schnittstelle, über die die PWA den Verbindungsstatus zum Hub aktiv überwacht sowie Projektserver steuert. Er ist verbindlich für alle Kommunikationsvorgänge zwischen PWA-Frontend und Hub-Backend.

**Zweck**

Die PWA muss jederzeit zuverlässig feststellen können, ob der Hub erreichbar ist, um Start- und Stopp-Aktionen korrekt zu sperren oder freizugeben (FR-05, FR-08). Darüber hinaus definiert dieser Contract die Endpunkte zum Abrufen des aktuellen Projektstatus sowie zum Starten und Stoppen von Projektservern (FR-01 bis FR-04, FR-06, FR-07).

**Garantien des Hubs**

- `GET /health` antwortet innerhalb von 500 ms mit einem maschinenlesbaren Verbindungsstatus und dient als Heartbeat für den Offline/Online-Wechsel.
- `GET /projects` liefert vollständige Statusdaten aller registrierten Projekte; der Aufruf ist für den initialen Ladevorgang auf eine Antwortzeit von ≤ 2 Sekunden ausgelegt.
- `POST /projects/{projectId}/start` und `POST /projects/{projectId}/stop` bestätigen den Befehl synchron mit HTTP 202; die resultierende Statusänderung ist innerhalb von ≤ 5 Sekunden im nächsten `GET /projects`-Abruf sichtbar.
- Alle Endpunkte verwenden `application/json`. Fehlercodes folgen dem RFC 7807 Problem-Detail-Format (`application/problem+json`).
- Aktionen gegen ein nicht erreichbares Hub führen zu einem Netzwerkfehler; die PWA leitet daraus den Offline-Modus ab und sperrt Schaltflächen (FR-05).

**Geltungsbereich**

Dieser Contract deckt ausschließlich die Betriebssteuerung bestehender Projekte ab. Das Anlegen, Konfigurieren oder Löschen von Projekten, die Verwaltung von Nutzern und Rollen sowie die Anzeige von Logs und Metriken liegen außerhalb des Geltungsbereichs.

**Konsumenten**

Einziger erlaubter Konsument ist die SDD-PWA. Dritte dürfen diese Endpunkte nicht ohne explizite Freigabe direkt aufrufen.