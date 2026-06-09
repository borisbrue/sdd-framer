---
id: TST-0187
project: ""
title: "HoldoutStatusFetcher Strategy (SSE + Fallback)"
level: unit
spec: SPEC-0043
contract: CON-0159
status: planned
framework: pytest
artifact: "tests/unit/test_tst_0187.py"
tags: [unit, holdout, sse, strategy]
---

# Test: HoldoutStatusFetcher Strategy

> **Level:** unit · **Spec:** SPEC-0043 · **Contract:** CON-0159 · **Status:** planned

## Was wird geprüft?

Die `HoldoutStatusFetcher`-Klasse (Strategy Pattern aus SPEC-0043 §6):
SSE-Event-Parsing, Reconnect-Backoff bei Verbindungsabbruch,
korrektes Mapping von API-Status auf interne Modelle.

## Vorbedingungen

- `HoldoutStatusFetcher` in `sdd_cli/holdout_status_fetcher.py`
- Kein echter Netzwerkaufruf (alle Netzwerkaufrufe gemockt)

## Ablauf

1. SSE-Event mit status=running wird korrekt geparst
2. SSE-Event mit status=failed + scenarios wird korrekt geparst
3. Verbindungsabbruch → Status wechselt auf "unknown"
4. Reconnect-Backoff: 2. Versuch nach Fehler wartet länger als 1. Versuch
5. Ungültiges JSON-Event wird ignoriert (kein Crash)
6. status=none → leeres scenarios-Array kein Fehler

## Erwartetes Ergebnis

- TC-01–02: HoldoutStatus-Objekte korrekt befüllt
- TC-03: status == "unknown" nach Abbruch
- TC-04: backoff_delay[1] > backoff_delay[0]
- TC-05: kein Exception bei malformed JSON
- TC-06: scenarios == [] bei status=none

## Negativfälle / Edge Cases

- Event ohne data-Feld → wird übersprungen
- data-Feld kein gültiges JSON → wird übersprungen

## Verknüpfung mit Contract

Dieser Test prüft konkret folgende Punkte aus CON-0159:

- [ ] HoldoutStatusEvent-Schema wird korrekt deserialisiert
- [ ] status enum [running, passed, failed, none] vollständig abgebildet
- [ ] Reconnect-Logik (INV-04 aus CON-0160 via StatusFetcher)

## Hinweise zur Implementierung

`HoldoutStatusFetcher` als Strategy mit `fetch(spec_id)` → AsyncGenerator[HoldoutStatusEvent].
Backoff via `itertools` oder `asyncio.sleep` mit konfigurierbaren Delays.
