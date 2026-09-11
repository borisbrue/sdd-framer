---
id: CON-0068
title: "container-start-slo"
type: performance
format: slo-yaml
spec: SPEC-0021
version: 0.3.0
status: draft
tests: [TST-0078]
---

# Contract: container-start-slo

> **Spec:** SPEC-0021 · **Typ:** Performance (SLO) · **Status:** draft

## Zweck

Definiert das SLO für den Container-Teil von `sdd start SPEC-XXXX` (CON-0065
G-01). Das SLO-Fenster reicht von der Befehlsausführung bis zu dem Punkt, an dem
der Container Befehle annimmt.

> **v0.3.0 (2026-09-11):** Drei Korrekturen (#123).
>
> - Der Contract sprach von `sdd dev start` und maß den Overhead von
>   `sdd dev exec`. Beide Befehle gibt es seit SPEC-0044 nicht mehr: `sdd start`
>   startet den Container, Befehle laufen direkt über die Runtime (CON-0065
>   G-05). Die Overhead-Zeile ist gestrichen. Ohne `sdd`-Wrapper bleibt kein
>   eigener Overhead zu messen, und die Laufzeit von `docker exec`/`podman exec`
>   liegt nicht in der Hand des Frameworks.
> - Unter „Messung" stand, TST-0078 messe automatisch und schlage bei mehr als
>   30 Sekunden fehl. Das stimmt nicht: TST-0078 ist ein Platzhalter, eine
>   Zeitmessung gibt es nicht. Das SLO ist damit Ziel, nicht geprüfte Zusage.
> - Das `artifact`-Feld zeigte auf eine nie angelegte `.slo.yaml` und ist
>   entfernt.

**Abgrenzung zu CON-0054** (extension-server-management): Health-Check-Probes
und Readiness-Signale nach dem eigentlichen Container-Start sind **nicht** Teil
dieses SLOs — sie liegen im Verantwortungsbereich der Extension (CON-0054).
Das SLO endet, wenn `$RUNTIME exec sdd-dev-spec-xxxx true` mit Exit-Code 0
antwortet.

## Service Level Objectives

| SLI | Ziel | Messfenster | Konsequenz |
|---|---|---|---|
| `sdd start` Wall-Clock (Image vorhanden, bis exec-ready) | < 30 s | Pro Run | Test-Failure, sobald gemessen wird |
| `sdd start` p95 über 10 Runs | < 20 s | 10 Runs | Optimierungsaufgabe |

## Messung

- **Voraussetzung:** Image lokal vorhanden (kein Image-Pull gemessen).
- **SLO-Endpunkt:** `$RUNTIME exec sdd-dev-spec-xxxx true` antwortet mit
  Exit-Code 0. `$RUNTIME` ist `docker.runtime` aus `.sdd/config.yaml`
  (`docker` oder `podman`).
- **Messmethode:** Wall-Clock vom Start von `sdd start` bis zum SLO-Endpunkt.
- **Stand:** Eine automatische Messung gibt es noch nicht. TST-0078 beschreibt
  den geplanten Ablauf.

## Verbindlichkeit

Das SLO gilt für lokale Entwicklung mit vorhandenem Image. Image-Pull-Zeiten
und Readiness-Probes aus CON-0054 sind explizit ausgeschlossen.
