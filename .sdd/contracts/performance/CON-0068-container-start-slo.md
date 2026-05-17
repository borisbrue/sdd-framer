---
id: CON-0068
title: "container-start-slo"
type: performance
format: slo-yaml
spec: SPEC-0021
version: 0.2.0
status: draft
artifact: "contracts/performance/container-start.slo.yaml"
tests: [TST-0078]
---

# Contract: container-start-slo

> **Spec:** SPEC-0021 · **Typ:** Performance (SLO) · **Status:** draft

## Zweck

Definiert das SLO für `sdd dev start SPEC-XXXX`. Das SLO-Fenster deckt die
Zeit von der Befehlsausführung bis zum Punkt ab, an dem `sdd dev exec` ohne
Fehler aufgerufen werden kann (Container bereit für Befehle).

**Abgrenzung zu CON-0054** (extension-server-management): Health-Check-Probes
und Readiness-Signale nach dem eigentlichen Container-Start sind **nicht** Teil
dieses SLOs — sie liegen im Verantwortungsbereich der Extension (CON-0054).
Das SLO endet wenn `docker exec sdd-dev-spec-xxxx true` mit Exit-Code 0 antwortet.

## Service Level Objectives

| SLI | Ziel | Messfenster | Konsequenz |
|---|---|---|---|
| `sdd dev start` Wall-Clock (Image vorhanden, bis exec-ready) | < 30 s | Pro Run | Test-Failure |
| `sdd dev start` p95 über 10 Runs | < 20 s | 10 Runs | Optimierungsaufgabe |
| `sdd dev exec` Overhead vs. lokalem Aufruf | < 500 ms | Pro Run | Warnung |

## Messung

- **Voraussetzung:** Docker-Image lokal vorhanden (kein Image-Pull gemessen).
- **SLO-Endpunkt:** `docker exec sdd-dev-spec-xxxx true` antwortet mit Exit-Code 0.
- **Messmethode:** Wall-Clock von `sdd dev start` Befehlsstart bis SLO-Endpunkt.
- **CI-Messung:** TST-0078 misst automatisch und schlägt fehl wenn > 30 Sekunden.

## Verbindlichkeit

Das SLO gilt für lokale Entwicklung mit vorhandenem Image. Image-Pull-Zeiten
und Readiness-Probes aus CON-0054 sind explizit ausgeschlossen.
