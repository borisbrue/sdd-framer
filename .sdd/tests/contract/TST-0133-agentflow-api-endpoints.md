---
id: TST-0133
project: ""
title: "AgentFlow API Endpoints"
level: contract
spec: SPEC-0032
contract: CON-0114
status: planned
framework: "pytest + httpx"
artifact: "tests/contract/test_agentflow_api.py"
tags: []
---

# Test: AgentFlow API Endpoints

> **Level:** contract · **Spec:** SPEC-0032 · **Contract:** CON-0114 · **Status:** planned

## Was wird geprüft?

Die drei neuen `/api/agent/flow/*` Endpunkte der `AgentFlowFacade` entsprechen dem
OpenAPI-Schema aus CON-0114: korrekte Request/Response-Schemata, HTTP-Statuscodes
und Fehlerfälle für `start`, `reply` und `GET state`.

## Vorbedingungen

- SDD-Server läuft (`sdd ui` oder Testfixture mit TestClient)
- Keine laufenden Flow-Sessions aus anderen Tests (isolierter State)
- SPEC-0032 existiert im Dateisystem (für review/implement-Flow-Tests)

## Ablauf

1. `POST /api/agent/flow/start` mit `flow_type: "new-spec"` senden
2. Antwort validieren: `session_id` (UUID), `prompt` (nicht leer), `state: "awaiting_input"`
3. `POST /api/agent/flow/{session_id}/reply` mit `answer: "TestSpec"` senden
4. Antwort validieren: entweder `{done: false, prompt: ..., state: "awaiting_input"}` oder `{done: true, job_id: ...}`
5. `GET /api/agent/flow/{session_id}` aufrufen
6. Antwort validieren: `session_id`, `flow_type: "new-spec"`, `step_index >= 0`, `answers` nicht leer

## Erwartetes Ergebnis

- `POST /start` → HTTP 200, Schema konform zu `FlowStartResponse`
- `POST /reply` → HTTP 200, Schema konform zu `FlowReplyResponse`
- `GET /{session_id}` → HTTP 200, Schema konform zu `FlowState`
- Alle Pflichtfelder vorhanden, keine unbekannten Properties

## Negativfälle / Edge Cases

- `POST /start` mit `flow_type: "unknown-type"` → HTTP 422
- `POST /start` ohne `flow_type` → HTTP 400
- `POST /start` mit `flow_type: "review"` ohne `spec_id` → HTTP 422
- `POST /reply` mit unbekannter `session_id` → HTTP 404
- `GET` mit abgelaufener / unbekannter `session_id` → HTTP 404
- `POST /reply` auf Session im State `done` → HTTP 409

## Verknüpfung mit Contract

Dieser Test prüft konkret folgende Punkte aus CON-0114:

- [x] `POST /api/agent/flow/start` — Pflichtfelder `session_id`, `prompt`, `state` in Response
- [x] `POST /api/agent/flow/{session_id}/reply` — `done`-Flag, `prompt` oder `job_id`
- [x] `GET /api/agent/flow/{session_id}` — vollständiger `FlowState` mit `answers`
- [x] HTTP 422 bei ungültigem `flow_type`
- [x] HTTP 404 bei unbekannter `session_id`
- [x] HTTP 409 bei Reply auf abgeschlossene Session

## Hinweise zur Implementierung

```python
# pytest + httpx AsyncClient gegen FastAPI TestClient
from fastapi.testclient import TestClient
from sdd_cli.web.api.app import app

client = TestClient(app)

def test_start_new_spec_flow():
    r = client.post("/api/agent/flow/start", json={"flow_type": "new-spec"})
    assert r.status_code == 200
    data = r.json()
    assert "session_id" in data
    assert data["state"] in ("awaiting_input", "running")
    assert data["prompt"]
```
