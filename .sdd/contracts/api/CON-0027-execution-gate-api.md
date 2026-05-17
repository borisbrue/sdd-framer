---
id: CON-0027
project: PRJ-0001
title: "Execution Gate – Web API Endpoints"
type: api
format: openapi
spec: SPEC-0014
version: 0.1.0
status: draft
artifact: "contracts/api/execution-gate-api.openapi.yaml"
tests: ["TST-0039"]
---

# Contract: Execution Gate – Web API Endpoints

> **Spec:** SPEC-0014 · **Typ:** API (OpenAPI) · **Status:** draft

## Zweck

REST-Endpunkte der sdd-web-api für den Execution-Gate-Prozess: Phasenstatus
abfragen, Phasen auslösen, Konflikte verwalten. Ermöglicht der Web UI (SPEC-0003)
den gesamten Gate-Flow ohne direkten CLI-Aufruf.

**Verhältnis zu CON-0007:** Dieser Contract deklariert sich als Sub-Contract
von CON-0007 (web-api). Alle hier definierten Routen sind unter dem
`/api/gate/` Prefix gruppiert, der in `web-api.openapi.yaml` als externes
$ref eingebunden wird. Kein Routing-Konflikt mit bestehenden Endpunkten.

## Geltungsbereich

- **In Scope:** Phasenstatus, Phasen-Trigger, Konflikt-Management, Override-Protokollierung
- **Out of Scope:** Orchestrator-Execution selbst (→ CON-0021), Analyse-Endpunkt (→ CON-0014)

## Endpunkte

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| `GET`   | `/api/gate/{spec_id}/status`              | Phasenstatus und phase_history lesen |
| `POST`  | `/api/gate/{spec_id}/spec-review`         | Phase 2: LLM-SPEC-Review auslösen (SSE) |
| `POST`  | `/api/gate/{spec_id}/contract-propose`    | Phase 3: Contract-Vorschläge generieren |
| `POST`  | `/api/gate/{spec_id}/contract-review`     | Phase 5: Konflikt-Analyse starten |
| `POST`  | `/api/gate/{spec_id}/test-generate`       | Phase 6: Tests generieren |
| `POST`  | `/api/gate/{spec_id}/approve`             | Phase 8: Finalen Konsistenzcheck auslösen |
| `GET`   | `/api/gate/{spec_id}/conflicts`           | Alle Konflikte der SPEC auflisten |
| `PATCH` | `/api/gate/{spec_id}/conflicts/{cf_id}`   | Konflikt auflösen oder acknowledgen |

## Verbindlichkeit

Dieser Contract ist **bindend**. Jede Implementierung MUSS:

1. das im Artifact (`contracts/api/execution-gate-api.openapi.yaml`) hinterlegte
   OpenAPI-Schema einhalten,
2. die Contract-Tests (siehe Frontmatter `tests:`) bestehen,
3. Breaking Changes nur mit Versions-Bump (MAJOR) und ADR einführen.

## Invarianten

- **INV-01:** Alle POST-Endpunkte geben HTTP 409 zurück wenn die Vorgängerphase
  noch nicht abgeschlossen ist.
- **INV-02:** `PATCH /conflicts/{cf_id}` ohne `reason` im Body gibt HTTP 422 zurück.
- **INV-03:** Phase-Trigger-Endpunkte (spec-review, contract-review, approve)
  streamen ihr LLM-Feedback als Server-Sent Events (SSE).
- **INV-04:** `GET /status` gibt immer HTTP 200 zurück, auch wenn kein
  Pipeline-JSON existiert (dann `pipeline_phase: null`).

## Versionierung

- **MAJOR:** Endpunkt entfernt, Pflichtfeld hinzugefügt, Response-Schema gebrochen
- **MINOR:** Neuer optionaler Endpunkt oder optionales Antwortfeld
- **PATCH:** Doku-/Beschreibungsänderungen

## Validierung

Schema-Artifact: `contracts/api/execution-gate-api.openapi.yaml`

- Schema-Linting: `spectral lint`
- Contract-Tests: `schemathesis run` gegen laufende sdd-web-api
