---
id: TST-0013
project: ""
title: "Analyze-Endpoint Integrations-Test"
level: integration
spec: SPEC-0005
contract: CON-0014
status: implemented
framework: "pytest"
artifact: "tests/integration/test_analyze_endpoint.py"
tags: ["guided", "ai-assist", "analyze", "anthropic-sdk"]
---

# Test: Analyze-Endpoint Integrations-Test

> **Level:** integration · **Spec:** SPEC-0005 · **Contract:** CON-0014 · **Status:** implemented

## Was wird geprüft?

Die Kerngarantien aus CON-0013 + CON-0014:
- Subprocess-Aufruf mit korrekten Argumenten (CON-0013 G-01)
- HTTP 503 wenn `claude` nicht im PATH (CON-0013 G-02)
- Session-Tracking: beantwortete Fragen erscheinen nicht erneut (CON-0014 INV-03)
- Maximal 5 Fragen pro Response (CON-0014 INV-01)
- HTTP 504 bei Subprocess-Timeout (CON-0013 INV-03)
- doc_type beeinflusst Prompt (CON-0013 G-04)

## Vorbedingungen

- FastAPI-Testclient (`TestClient` aus `fastapi.testclient`)
- `anthropic.Anthropic` wird gemockt via `unittest.mock.patch` — kein echter API-Aufruf
- `pytest` mit `monkeypatch`
- `ANTHROPIC_API_KEY` wird im Test-Setup gesetzt bzw. für TC-03 entfernt

## Ablauf

### TC-01: Happy Path — Spec-Analyse

1. Mocke `subprocess.run` → gibt valides JSON mit 3 Fragen zurück
2. `PUT /api/docs/SPEC-0001/analyze` mit `doc_type: "spec"`, leerem `answered_questions`
3. Prüfe: HTTP 200
4. Prüfe: `questions` hat ≤ 5 Einträge
5. Prüfe: jede Question hat `id`, `section`, `text`, `severity`
6. Prüfe: `session_id` ist gesetzt

### TC-02: Session-Tracking — beantwortete Fragen werden nicht wiederholt

1. Erster Aufruf: Response enthält `q1`, `q2`
2. Zweiter Aufruf mit `answered_questions: [{ "id": "q1", "answer": "..." }]`
3. Prüfe: Subprocess-Prompt des zweiten Aufrufs enthält die Antwort auf q1
4. Mocke Claude so dass q1 nicht mehr zurückgegeben wird
5. Prüfe: `q1` erscheint nicht in zweiter Response (INV-03)

### TC-03: ANTHROPIC_API_KEY fehlt → HTTP 503

1. Entferne `ANTHROPIC_API_KEY` aus der Umgebung (`monkeypatch.delenv`)
2. `PUT /api/docs/SPEC-0001/analyze`
3. Prüfe: HTTP 503
4. Prüfe: `detail` enthält `"ANTHROPIC_API_KEY"`

### TC-04: API-Timeout → HTTP 504

1. Mocke `anthropic.Anthropic.messages.create` → wirft `anthropic.APITimeoutError`
2. Prüfe: HTTP 504
3. Prüfe: `detail.error == "claude_timeout"`

### TC-05: Claude gibt kein valides JSON → HTTP 502

1. Mocke `subprocess.run` → gibt `"Ich bin ein Sprachmodell und..."` zurück
2. Prüfe: HTTP 502
3. Prüfe: `error == "claude_parse_error"`, `raw` enthält ersten Teil des Outputs

### TC-06: doc_type beeinflusst Prompt

1. Zwei Aufrufe: einmal `doc_type: "spec"`, einmal `doc_type: "contract"`
2. Prüfe: Subprocess-Prompt enthält jeweils anderen Template-Inhalt
3. Prüfe: beide Aufrufe erfolgreich (HTTP 200)

### TC-07: Maximal 5 Fragen

1. Mocke Claude so dass 8 Fragen zurückgegeben werden
2. Prüfe: Response enthält maximal 5 Fragen (INV-01)
   - Entweder: Prompt enthält "maximal 5"-Anweisung und Claude hält sich daran
   - Oder: Server schneidet auf 5 ab

## Erwartetes Ergebnis

Alle 7 Test-Cases + 3 Edge-Case-Tests bestehen mit gemockter `anthropic`-Bibliothek — kein echter API-Aufruf nötig. Laufbefehl: `uv run pytest tests/integration/test_analyze_endpoint.py -v` (aus `web/api/`).

## Negativfälle / Edge Cases

- Leerer `content`-String → HTTP 422 (Validierungsfehler)
- `doc_type` ungültig → HTTP 422
- Sehr langer Inhalt (> 50 000 Zeichen) → Prompt wird auf sinnvolle Länge gekürzt

## Verknüpfung mit Contract

Dieser Test prüft konkret folgende Punkte aus CON-0014:

- [x] INV-01: max. 5 Fragen (TC-07)
- [x] INV-03: answered_questions erscheinen nicht erneut (TC-02)
- [x] INV-04: session_id immer gesetzt (TC-01)
- [x] HTTP 503 bei fehlendem ANTHROPIC_API_KEY (TC-03)
- [x] HTTP 504 bei Timeout (TC-04)
- [x] HTTP 502 bei Parse-Fehler (TC-05)

## Hinweise zur Implementierung

```python
from unittest.mock import MagicMock, patch
import json

def _make_api_response(questions=None):
    payload = json.dumps({"questions": questions or [], "issues": [], "suggestions": []})
    msg = MagicMock()
    msg.content = [MagicMock(text=payload)]
    msg.usage = MagicMock(input_tokens=100, output_tokens=50,
                          cache_creation_input_tokens=0, cache_read_input_tokens=0)
    return msg

# Verwendung:
mock_client = MagicMock()
mock_client.messages.create.return_value = _make_api_response()
with patch("analyzer.anthropic.Anthropic", return_value=mock_client):
    res = client.put("/api/docs/SPEC-TEST/analyze", json={...})
```
