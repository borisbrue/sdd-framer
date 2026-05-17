---
id: TST-0025
project: PRJ-0001
title: "Orchestrate Endpoints – Integration"
level: integration
spec: SPEC-0007
contract: CON-0021
status: implemented
framework: pytest
artifact: "tests/integration/test_orchestrate_endpoints.py"
tags: ["orchestrate", "api", "execute-flow"]
---

# Test: Orchestrate Endpoints – Integration

Tests für `POST /api/orchestrate`, `GET /api/pipeline/{run_id}` und
`GET /api/pipeline/active` gegen den FastAPI TestClient.

## Test Cases

| TC    | Beschreibung                                         | Erwartet         |
|-------|------------------------------------------------------|------------------|
| TC-01 | `POST /orchestrate` mit approved Spec                | 202 + run_id     |
| TC-02 | `POST /orchestrate` mit non-approved Spec            | 422              |
| TC-03 | `POST /orchestrate` mit unbekannter Spec-ID          | 404              |
| TC-04 | Zweites `POST /orchestrate` für dieselbe Spec        | 409              |
| TC-05 | `POST /orchestrate` ohne claude CLI                  | 503              |
| TC-06 | `GET /pipeline/{run_id}` für existierenden Run       | 200 + state      |
| TC-07 | `GET /pipeline/{run_id}` für unbekannten Run         | 404              |
| TC-08 | `GET /pipeline/active?spec_id=X` bei aktivem Lauf   | 200 + state      |
| TC-09 | `GET /pipeline/active?spec_id=X` ohne aktiven Lauf  | 404              |
