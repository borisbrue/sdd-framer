---
id: CON-XXXX
project: ""                # PRJ-XXXX
title: "<Performance-Aspekt>"
type: performance
format: slo-yaml
spec: SPEC-XXXX
version: 0.1.0
status: draft
artifact: "contracts/performance/<name>.slo.yaml"
tests: []
---

# Contract: {{title}}

> **Spec:** {{spec}} · **Typ:** Performance (SLO) · **Status:** {{status}}

## Service Level Objectives (SLOs)

| SLI                     | Ziel       | Messfenster | Konsequenz bei Verletzung      |
|-------------------------|------------|-------------|-------------------------------|
| Latenz p95 (GET /...)   | < 200 ms   | 30 Tage     | Alert + Rollback-Kandidat     |
| Verfügbarkeit           | ≥ 99.9 %   | 30 Tage     | Incident Review               |
| Fehlerquote (5xx)       | < 0.1 %    | 24 Stunden  | Auto-Page                     |

## Messung

- **Datenquelle:** <z.B. Prometheus, Datadog>
- **Erhebung:** <z.B. RED-Metrics auf API-Gateway>
- **Tests:** Lasttests mit k6/Locust/Gatling laufen vor jedem Release

## Error Budget

Wird das Budget innerhalb des Messfensters verbraucht, gilt ein Feature-Freeze, bis die SLOs wieder eingehalten werden.
