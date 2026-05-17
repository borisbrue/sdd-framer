---
id: TST-0039
title: "Execution Gate – Web API Endpoints"
level: contract
spec: SPEC-0014
contract: CON-0027
status: implemented
framework: pytest
artifact: "tests/contract/test_con-0027.py"
tags: [gate, api, http]
---

# Test: Execution Gate – Web API Endpoints (CON-0027)

> **Level:** contract · **Spec:** SPEC-0014 · **Contract:** CON-0027

## Was wird geprüft?

Alle 8 Gate-Routen unter `/api/gate/{spec_id}/`: HTTP-Statuscodes, Fehlerbehandlung, Orchestrate-Gate-Enforcement.

## Vorbedingungen

- `web/api/routes/gate.py` implementiert
- FastAPI TestClient verfügbar

## Ablauf

1. `GET /gate/{id}/status` → 200 auch ohne Pipeline-JSON
2. `POST /gate/{id}/contract-review` → 409 wenn Vorgängerphase fehlt
3. `GET /gate/{id}/conflicts` → 404 wenn kein Bericht
4. `PATCH /gate/{id}/conflicts/{cf_id}` ohne `reason` bei acknowledge → 422
5. `PATCH /gate/{id}/conflicts/{cf_id}` mit `action=resolve` → 200
6. `POST /orchestrate` → 409 wenn `pipeline_phase != execute-unlocked`
7. `POST /orchestrate` mit `force+override_reason` → 202 trotz Gate
8. `POST /orchestrate` mit `force` ohne `override_reason` → 422

## Verknüpfung mit Contract

- [x] INV-01: Phase-Trigger 409 wenn Vorgänger fehlt
- [x] INV-02: acknowledge ohne reason → 422
- [x] INV-04: GET /status immer 200
