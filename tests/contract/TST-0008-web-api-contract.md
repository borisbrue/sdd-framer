---
id: TST-0008
title: "web-api-contract"
level: contract
spec: SPEC-0003
contract: CON-0007
status: planned
framework: schemathesis
artifact: "tests/contract/test_web_api_contract.py"
tags: [api, openapi, schemathesis]
---

# Test: web-api-contract

> **Level:** contract · **Spec:** SPEC-0003 · **Contract:** CON-0007 · **Status:** planned

## Was wird geprüft?

Alle im OpenAPI-Schema (CON-0007, `contracts/api/web-api.openapi.yaml`) definierten Endpunkte liefern Antworten, die dem deklarierten Schema entsprechen. Schemathesis generiert aus dem OpenAPI-Dokument automatisch Testfälle und prüft jeden Endpunkt gegen das deklarierte Request/Response-Schema.

## Vorbedingungen

- SDD-Server läuft auf `http://localhost:8000` gegen ein Test-SDD-Projekt
- Python-Abhängigkeiten: `schemathesis`, `pytest`, `requests`
- Das Test-SDD-Projekt enthält: min. 1 Spec, 1 Contract, 1 Test, 1 Projekt

## Ablauf

1. Schemathesis lädt das OpenAPI-Schema von `GET /openapi.json` (FastAPI-Autodoc)
2. Für jeden deklarierten Endpunkt generiert Schemathesis gültige und ungültige Eingaben
3. Jede Response wird auf korrekten HTTP-Status und Schema-Konformität geprüft
4. Zusätzliche manuelle Testfälle sichern kritische Garantien ab (s.u.)

## Erwartetes Ergebnis

- Alle `2xx`-Responses entsprechen dem deklarierten Response-Schema
- `GET /api/projects` gibt ein Array von Project-Objekten zurück (inkl. `autonomy_level`)
- `PATCH /api/projects/{id}/level` mit ungültigem Level gibt `422` zurück
- `POST /api/validate` gibt `errors` und `warnings` je mit `file`, `message` und `instruction` zurück
- `GET /api/maintenance` gibt `total_issues`, `stale_specs`, `drift_issues`, `issues[]` zurück
- Fehlende Ressourcen (z.B. unbekannte Spec-ID) geben `404` zurück

## Negativfälle / Edge Cases

- `PATCH /api/projects/{id}/level` mit `level: 99` → `422 Unprocessable Entity`
- `GET /api/specs/NONEXISTENT` → `404 Not Found`
- `POST /api/projects` ohne `name`-Feld → `422 Unprocessable Entity`
- `PUT /api/docs/{doc_id}/analyze` mit leerem `content` → valide Response (kein 500)

## Verknüpfung mit Contract

Dieser Test prüft konkret folgende Punkte aus CON-0007:

- [x] G-01: GET /projects gibt Project[] zurück
- [x] G-02: PATCH /projects/{id}/level setzt autonomy_level
- [x] G-03: POST /validate gibt ValidationResult mit instruction-Feld zurück
- [x] G-04: GET /maintenance gibt MaintenanceReport zurück
- [x] G-05: Alle Schemas sind OpenAPI 3.1.0 konform
- [ ] G-06: AI-Endpunkte (nur Smoke-Test, kein echter Claude-Aufruf in CI)

## Hinweise zur Implementierung

```python
# tests/contract/test_web_api_contract.py
import schemathesis

schema = schemathesis.from_uri("http://localhost:8000/openapi.json")

@schema.parametrize()
def test_api_contract(case):
    response = case.call()
    case.validate_response(response)
```

Für CI: Server vorher per `pytest-subprocess` oder `subprocess.Popen` starten.
AI-Endpunkte (`/api/ai/*`, `/api/copilot/*`) mit `schema.parametrize(endpoint="/api/ai")` ausschließen oder als Smoke-Test markieren (`@pytest.mark.skip(reason="requires claude CLI")`).
