---
id: CON-0151
project: ''
title: Antwortzeitanforderungen (SLO)
type: performance
format: slo-yaml
spec: SPEC-0040
version: 0.1.0
status: draft
artifact: contracts/performance/antwortzeitanforderungen-slo.slo.yaml
tests:
- TST-0175
---
Dieser Contract legt die messbaren Antwortzeitgarantien (Service Level Objectives, SLOs) für die Integration der PWA mit dem Hub fest. Er gilt für alle Interaktionen zwischen PWA-Client und Hub-API gemäß der übergeordneten Spec.

**Zweck**
Die definierten SLOs stellen sicher, dass Nutzer zeitnah valide Statusinformationen erhalten und Steuerungsaktionen (Start/Stopp) ohne spürbare Verzögerung ausgeführt werden. Sie bilden die verbindliche Grundlage für Monitoring, Alerting und Akzeptanztests.

**Garantien**
- Der initiale Projektstatus-Abruf nach dem Öffnen der PWA schließt innerhalb von **≤ 2 Sekunden** ab (p95).
- Eine Start- oder Stopp-Aktion führt innerhalb von **≤ 5 Sekunden** zu einer sichtbaren Statusänderung in der UI (p95).
- Die PWA erkennt einen Verbindungsverlust zum Hub und zeigt den Offline-Hinweis innerhalb von **≤ 3 Sekunden** an (p99).
- Nach erfolgreichem Laden sind **100 %** der hinterlegten Projekte in der Projektliste sichtbar.
- Start- und Stopp-Schaltflächen sind bei fehlendem Hub-Kontakt zu **100 %** deaktiviert (null Phantomaktionen).

**Geltungsbereich**
Die SLOs gelten für Endnutzer-Interaktionen unter normalen Netzwerkbedingungen (LAN/WLAN, Latenz < 100 ms zum Hub). Extern verursachte Ausfälle des Hubs oder der Projektserver selbst fallen nicht in den Geltungsbereich dieses Contracts.

**Messung & Reporting**
Alle SLIs werden clientseitig per Performance-Instrumentierung (z. B. `performance.mark` / `performance.measure`) sowie serverseitig über Hub-API-Metriken erfasst. Das Fehlerfenster wird als gleitendes 7-Tage-Fenster berechnet.