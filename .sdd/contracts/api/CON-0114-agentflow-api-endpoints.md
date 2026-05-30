---
id: CON-0114
project: ""                # PRJ-XXXX
title: "AgentFlow API Endpoints"
type: api
format: openapi
spec: SPEC-0032
version: 0.1.0
status: active
artifact: ".sdd/contracts/api/agentflow-api-endpoints.openapi.yaml"
tests: ["TST-0133"]                  # zugehörige Test-IDs
---

# Contract: AgentFlow API Endpoints

> **Spec:** SPEC-0032 · **Typ:** API (OpenAPI) · **Status:** draft

## Zweck

Definiert die drei neuen REST-Endpunkte der `AgentFlowFacade` (SPEC-0032):
- `POST /api/agent/flow/start` — startet eine neue Flow-Session (FR-01)
- `POST /api/agent/flow/{session_id}/reply` — sendet eine Nutzer-Antwort (FR-02)
- `GET /api/agent/flow/{session_id}` — gibt den aktuellen Flow-State zurück (FR-06)

Diese Endpunkte sind der einzige Kommunikationskanal zwischen PWA und den
bestehenden Subsystemen (SPEC-0005, SPEC-0007, SPEC-0016). Bestehende Endpunkte
werden nicht verändert.

## Geltungsbereich

- **In Scope:** Die drei neuen `/api/agent/flow/*` Endpunkte; Request/Response-Schemata; Fehlercodes
- **Out of Scope:** Interne Job-Polling-Endpunkte (SPEC-0016, SPEC-0007); Push-Notification-Protokoll (SPEC-0023); Tunnel-Konfiguration (CON-0116)

## Verbindlichkeit

Dieser Contract ist **bindend**. Jede Implementierung MUSS:

1. das im Artifact (`.sdd/contracts/api/agentflow-api-endpoints.openapi.yaml`) hinterlegte OpenAPI-Schema einhalten,
2. die Contract-Tests (siehe Frontmatter `tests:`) bestehen,
3. Breaking Changes nur mit Versions-Bump (MAJOR) und ADR einführen.

## Versionierung

Semantic Versioning für den Contract selbst:

- **MAJOR:** Breaking Change am Schema (z.B. Feld entfernt, Typ geändert)
- **MINOR:** Additiv (neues optionales Feld, neuer Endpoint)
- **PATCH:** Doku-/Beschreibungsänderungen

## Validierung

Der eigentliche Schema-Artifact liegt unter `.sdd/contracts/api/agentflow-api-endpoints.openapi.yaml`. Validierung erfolgt durch:

- Schema-Linting (z.B. `spectral lint`)
- Contract-Tests gegen die Implementierung (z.B. `schemathesis`, `dredd`, `pact`)
