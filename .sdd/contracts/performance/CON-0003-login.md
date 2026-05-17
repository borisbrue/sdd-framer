---
id: CON-0003
title: "Login Performance SLOs"
type: performance
format: slo-yaml
spec: SPEC-0001
version: 1.0.0
status: active
artifact: "contracts/performance/login.slo.yaml"
tests: [TST-0004]
---

# Contract: Login Performance SLOs

> **Spec:** SPEC-0001 · **Typ:** Performance · **Status:** active

## Service Level Objectives

| SLI                            | Ziel       | Messfenster | Konsequenz bei Verletzung   |
|--------------------------------|------------|-------------|-----------------------------|
| Latenz p95 POST /v1/auth/login | < 300 ms   | 30 Tage     | Alert + Rollback-Kandidat   |
| Latenz p99                     | < 800 ms   | 30 Tage     | Warning                     |
| Verfügbarkeit                  | ≥ 99.9 %   | 30 Tage     | Incident Review             |
| Fehlerquote 5xx                | < 0.1 %    | 24 Stunden  | Auto-Page                   |

## Messung

- **Datenquelle:** Prometheus (Histogramm `http_request_duration_seconds{route="/v1/auth/login"}`)
- **Pre-Release-Validierung:** k6-Lasttest (TST-0004) gegen Staging mit 100 RPS für 5 Minuten
- **Error Budget:** Bei < 99.9 % Verfügbarkeit im 30-Tage-Fenster → Feature-Freeze für Auth-Bereich

## Verbindlichkeit

Die SLO-Definition liegt maschinenlesbar in `contracts/performance/login.slo.yaml` und wird in Alerting-Regeln und Lasttests referenziert.
