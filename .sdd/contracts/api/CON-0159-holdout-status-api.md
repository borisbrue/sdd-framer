---
id: CON-0159
project: ""
title: "Holdout-Status API"
type: api
format: openapi
spec: SPEC-0043
version: 0.1.0
status: approved
artifact: "contracts/api/CON-0159-holdout-status-api.openapi.yaml"
tests: ["TST-0185", "TST-0187"]
---

# Contract: Holdout-Status API

> **Spec:** SPEC-0043 · **Typ:** API (OpenAPI) · **Status:** draft

## Zweck

Garantiert das Request/Response-Schema für `GET /api/holdouts/{spec_id}` –
den Endpunkt der den aktuellen Holdout-Status (neuester Lauf) sowie
Szenario-Details für eine gegebene Spec zurückgibt.
Deckt FR-04 aus SPEC-0043 ab.

## Geltungsbereich

- **In Scope:** `GET /api/holdouts/{spec_id}` – Status + Szenario-Details des neuesten Laufs
- **Out of Scope:** Starten/Stoppen von Holdout-Läufen, historische Läufe, SSE-Stream-Endpunkt

## Verbindlichkeit

Dieser Contract ist **bindend**. Jede Implementierung MUSS:

1. das im Artifact (`contracts/api/CON-0159-holdout-status-api.openapi.yaml`) hinterlegte OpenAPI-Schema einhalten,
2. die Contract-Tests (siehe Frontmatter `tests:`) bestehen,
3. Breaking Changes nur mit Versions-Bump (MAJOR) und ADR einführen.

## Versionierung

- **MAJOR:** Breaking Change am Schema (Feld entfernt, Typ geändert, Status-Wert entfernt)
- **MINOR:** Additiv (neues optionales Feld, neuer Status-Wert)
- **PATCH:** Doku-/Beschreibungsänderungen

## Validierung

Validierung erfolgt durch:

- Schema-Linting (`spectral lint`)
- Contract-Tests gegen die Implementierung (`schemathesis`)
