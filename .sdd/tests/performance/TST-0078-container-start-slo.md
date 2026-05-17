---
id: TST-0078
project: PRJ-0001
title: "Performance Test: Container-Start SLO"
contract: CON-0068
contracts: ["CON-0068"]
spec: SPEC-0021
level: performance
status: draft
artifact: "tests/performance/test_container_start_slo.py"
---

# Performance Test: Container-Start SLO

> **Contract:** CON-0068 · **Typ:** Performance-Test · **Status:** draft

## Abgedeckte SLOs

- CON-0068: `sdd start` Wall-Clock < 30 s (Image vorhanden)
- CON-0068: p95 über 10 Runs < 20 s

## Test-Datei

`tests/performance/test_container_start_slo.py`

## Testablauf

```
Voraussetzung: Docker-Image lokal vorhanden (kein Pull)

Für n=10 Runs:
  1. sdd start SPEC-TEST-PERF-001  → Zeit messen
  2. sdd close SPEC-TEST-PERF-001  → aufräumen

Ergebnis:
  - Max-Zeit < 30 s (hart)
  - p95 < 20 s (weich)
```

## Akzeptanzkriterien

- [ ] Kein einzelner Run überschreitet 30 Sekunden
- [ ] p95 über 10 Runs liegt unter 20 Sekunden
- [ ] Messung schließt nur `sdd start` ein, nicht Image-Pull-Zeit
