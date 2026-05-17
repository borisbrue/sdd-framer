---
id: CON-0073
title: "log-latency-slo"
type: performance
format: slo-yaml
spec: SPEC-0022
version: 0.1.0
status: draft
artifact: "contracts/performance/log-latency.slo.yaml"
tests: [TST-0083]
---

# Contract: log-latency-slo

> **Spec:** SPEC-0022 · **Typ:** Performance (SLO) · **Status:** draft

## Service Level Objectives

| SLI | Ziel | Messfenster | Konsequenz |
|---|---|---|---|
| Log-Latenz: Container-Ausgabe → WebSocket-Client | < 1 s | Pro Zeile | Test-Failure |
| Log-Latenz p95 | < 500 ms | 100 Zeilen | Optimierungsaufgabe |
| Buffer-History Übertragungszeit (500 Zeilen) | < 2 s | Pro Connect | Test-Failure |

## Messung

- **Log-Latenz:** Zeit von der Ausgabe einer Log-Zeile im Container bis zum
  Empfang der JSON-Nachricht beim WebSocket-Client.
- **Messmethode:** Test-Client misst `recv_ts - container_output_ts` (beide im
  selben Prozess für deterministische Messung).
- **CI:** TST-0083 führt 100 Messungen durch und prüft p95 < 500 ms.
