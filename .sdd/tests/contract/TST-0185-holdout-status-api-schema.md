---
id: TST-0185
project: ""
title: "Holdout-Status API Schema-Konformität"
level: contract
spec: SPEC-0043
contract: CON-0159
status: planned
framework: pytest + httpx (FastAPI TestClient)
artifact: "tests/contract/test_tst_0185.py"
tags: [api, holdout, contract]
---

# Test: Holdout-Status API Schema-Konformität

> **Level:** contract · **Spec:** SPEC-0043 · **Contract:** CON-0159 · **Status:** planned

## Was wird geprüft?

Response-Schema von `GET /api/holdouts/{spec_id}` und `GET /api/holdouts/{spec_id}/stream`
gegen das OpenAPI-Schema in CON-0159. HTTP-Statuscodes, Pflichtfelder, Enum-Werte,
Fehlerfälle (404, 422, 500).

## Vorbedingungen

- FastAPI-App mit Route `/api/holdouts/{spec_id}` registriert
- TestClient mit gemocktem HoldoutService

## Ablauf

1. GET /api/holdouts/SPEC-0043 → Holdout existiert (status=passed)
2. GET /api/holdouts/SPEC-9999 → kein Lauf (404)
3. GET /api/holdouts/INVALID → ungültige ID (422)
4. GET /api/holdouts/SPEC-0043/stream → Content-Type text/event-stream
5. GET /api/holdouts/SPEC-0043 bei status=failed → scenarios-Feld befüllt

## Erwartetes Ergebnis

- TC-01: 200, spec_id + status + updated_at vorhanden, status ∈ {running,passed,failed,none}
- TC-02: 404, Error-Schema (code + message)
- TC-03: 422, Error-Schema
- TC-04: 200, Content-Type: text/event-stream
- TC-05: 200, scenarios ist Array mit name + status Feldern

## Negativfälle / Edge Cases

- status=none → scenarios darf leer sein (kein Fehler)
- run_id=null ist valid bei status=none

## Verknüpfung mit Contract

Dieser Test prüft konkret folgende Punkte aus CON-0159:

- [ ] HoldoutStatus.required: [spec_id, status, updated_at]
- [ ] status enum: [running, passed, failed, none]
- [ ] ScenarioResult.required: [name, status]
- [ ] HTTP 404 bei nicht vorhandenem Lauf
- [ ] HTTP 422 bei ungültiger spec_id
- [ ] SSE-Endpunkt liefert text/event-stream
- [ ] HTTP 500 auf SSE-Stream bei Serverfehler

## Hinweise zur Implementierung

Route muss in `tool/sdd_cli/web/api/routes/holdouts.py` registriert werden.
TestClient aus `web/api/main.py` app-Instanz nutzen (vgl. test_con_0027.py).
