---
id: TST-0134
project: ""
title: "FlowSession State Machine Behavior"
level: contract
spec: SPEC-0032
contract: CON-0115
status: planned
framework: "pytest-bdd"
artifact: "tests/contract/test_flowsession_behavior.py"
tags: []
---

# Test: FlowSession State Machine Behavior

> **Level:** contract · **Spec:** SPEC-0032 · **Contract:** CON-0115 · **Status:** planned

## Was wird geprüft?

Die Zustandsübergänge der `FlowSession` State Machine gemäß CON-0115 (Gherkin):
- Happy Path vom ersten Prompt bis `done`
- Decision Point: Pause → Push-Notification → Nutzerantwort → Fortsetzung
- PWA-Reconnect: Session-State nach App-Neustart wiederherstellbar
- INV-01–INV-04: keine weiteren Replies nach `done`/`failed`; nur `ja`/`nein` bei Decision Points

## Vorbedingungen

- SDD-Server mit in-memory FlowSessionStore (kein persistenter State zwischen Tests)
- Mock für SPEC-0016-JobStore (review-Delegation) und SPEC-0007-PipelineRunState (implement-Delegation)
- Push-Notification-Kanal gemockt (kein echter PWA-Push-Aufruf in Tests)

## Ablauf

1. Flow starten (`POST /api/agent/flow/start`)
2. Alle Schritte des Flows mit gültigen Antworten durchlaufen
3. Nach letztem Schritt: `done: true` verifizieren
4. Decision-Point-Szenario: `state: "awaiting_decision"` auslösen, mit `"ja"` antworten, Fortsetzung prüfen
5. Reconnect-Szenario: `GET /api/agent/flow/{session_id}` aufrufen, vollständigen State inklusive `answers` prüfen
6. TTL-Szenario: Session als abgelaufen simulieren, HTTP 404 verifizieren

## Erwartetes Ergebnis

- Happy Path endet mit `state: "done"`, `done: true` in der letzten Reply
- Decision Point: `state: "awaiting_decision"` → `"ja"` → State wechselt zurück zu `"running"`
- Decision Point: `"nein"` → Schritt verworfen, Flow fährt fort, kein `"failed"`
- Reconnect: `GET` liefert `step_index`, `answers`, `current_prompt` unverändert
- TTL abgelaufen: HTTP 404, kein Crash
- INV-01: Reply auf `done`-Session → HTTP 409

## Negativfälle / Edge Cases

- `POST /reply` mit `answer: "vielleicht"` bei `awaiting_decision` → HTTP 422
- `POST /reply` auf `failed`-Session → HTTP 409
- `POST /reply` auf `running`-Session (Job läuft, kein Input erwartet) → HTTP 409
- Review-Flow: `job_id` in `done`-Response referenziert SPEC-0016-AnalysisJob (nicht neuen Store)
- Implement-Flow: `job_id` referenziert SPEC-0007-PipelineRun (nicht neuen Store)

## Verknüpfung mit Contract

Dieser Test prüft konkret folgende Punkte aus CON-0115:

- [x] INV-01: `done`/`failed` Session akzeptiert keine weiteren Replies (HTTP 409)
- [x] INV-02: `awaiting_decision` akzeptiert nur `"ja"` / `"nein"` (HTTP 422 sonst)
- [x] INV-03: TTL-abgelaufene Session → HTTP 404
- [x] INV-04: ReviewFlow / ImplementFlow nutzen keine eigene Job-Store-Instanz
- [x] Szenario: Happy Path → `done`
- [x] Szenario: Decision Point mit `"ja"` → Fortsetzung
- [x] Szenario: Decision Point mit `"nein"` → Schritt-Verwurf, kein `"failed"`
- [x] Szenario: PWA-Reconnect → `GET` liefert vollständigen State

## Hinweise zur Implementierung

```python
# pytest-bdd bindet die .feature-Datei aus CON-0115 direkt ein
from pytest_bdd import scenarios, given, when, then

scenarios("../../contracts/behavior/flowsession-state-machine-behavior.feature")

@given("der Nutzer startet einen Flow mit flow_type \"new-spec\"")
def start_new_spec(client):
    resp = client.post("/api/agent/flow/start", json={"flow_type": "new-spec"})
    assert resp.status_code == 200
    return resp.json()
```
