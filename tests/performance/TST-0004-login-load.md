---
id: TST-0004
title: "Performance: Login unter Last"
level: performance
spec: SPEC-0001
contract: CON-0003
status: planned
framework: k6
artifact: "tests/performance/login.k6.js"
tags: [auth, performance, load]
---

# Test: Performance Login unter Last

> **Level:** performance · **Spec:** SPEC-0001 · **Contract:** CON-0003

## Was wird geprüft?

Die in CON-0003 definierten SLOs werden vor jedem Release auf der Staging-Umgebung validiert:

- p95 Latenz < 300 ms
- p99 Latenz < 800 ms
- Fehlerquote < 0.1 %

## Vorbedingungen

- Staging-Umgebung mit produktionsähnlicher Hardware/Konfiguration
- Test-Accounts: mindestens 1000 vorab angelegt (zur Vermeidung von Brute-Force-Sperren)
- Rate-Limit für Lasttest-IP-Range entschärft

## Ablauf

1. k6 lädt Test-Accounts aus CSV
2. Stufenweiser Lastanstieg: 0 → 100 RPS über 1 min
3. Plateau: 100 RPS für 5 min
4. Abkühlung: 100 → 0 RPS über 1 min
5. Auswertung gegen Schwellwerte aus CON-0003

## Erwartetes Ergebnis

k6-Thresholds bestanden:

```javascript
thresholds: {
  http_req_duration: ['p(95)<300', 'p(99)<800'],
  http_req_failed: ['rate<0.001'],
}
```

## Negativfälle

- Memory Leak unter Last → Fail (Metriken aus Prometheus parallel beobachten)
- DB-Connection-Pool erschöpft → Fail
- 429-Antworten häufen sich → Konfigurationsfehler, nicht App-Fehler

## Verknüpfung mit Contract

Dieser Test verifiziert direkt die SLO-Targets aus `contracts/performance/login.slo.yaml`:

- [x] `latency_p95` (< 300 ms)
- [x] `latency_p99` (< 800 ms)
- [x] `error_rate_5xx` (< 0.1 %)

## Hinweise zur Implementierung

k6-Skript nutzt eine vorab generierte CSV mit `(email, password)`-Paaren. Das CI-Pipeline-Stage "load-test" läuft nur vor Promotion auf Production.
