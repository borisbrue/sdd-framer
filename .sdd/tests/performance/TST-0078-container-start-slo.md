---
id: TST-0078
project: PRJ-0001
title: "Performance Test: Container-Start SLO"
contract: CON-0068
contracts: ["CON-0068"]
spec: SPEC-0021
level: performance
status: draft
artifact: "tests/unit/test_tst_0078.py"
---

# Performance Test: Container-Start SLO

> **Contract:** CON-0068 · **Typ:** Performance-Test · **Status:** draft

## Stand

**Nicht umgesetzt.** `tests/unit/test_tst_0078.py` ist ein Platzhalter. Er prüft
nur die deterministischen Namen aus CON-0065 INV-01/INV-02, keine Zeit. Die
früher genannte Datei `tests/performance/test_container_start_slo.py` wurde nie
angelegt (#123).

## Abgedeckte SLOs (geplant)

- CON-0068: `sdd start` Wall-Clock < 30 s (Image vorhanden)
- CON-0068: p95 über 10 Runs < 20 s

## Geplanter Ablauf

```
Voraussetzung: Image lokal vorhanden (kein Pull)

Für n=10 Runs:
  1. sdd start SPEC-TEST-PERF-001            → Zeit bis exec-ready messen
  2. $RUNTIME rm -f sdd-dev-spec-test-perf-001 → aufräumen

Ergebnis:
  - Max-Zeit < 30 s (hart)
  - p95 < 20 s (weich)
```

Aufgeräumt wird direkt über die Runtime. Einen `sdd`-Befehl dafür gibt es seit
SPEC-0044 nicht mehr (`sdd dev close` ist entfallen). Im normalen Ablauf räumt
die Finalisierung auf (CON-0065 G-06).

## Akzeptanzkriterien

- [ ] Kein einzelner Run überschreitet 30 Sekunden
- [ ] p95 über 10 Runs liegt unter 20 Sekunden
- [ ] Messung schließt nur `sdd start` ein, nicht Image-Pull-Zeit
