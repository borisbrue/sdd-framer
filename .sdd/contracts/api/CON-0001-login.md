---
id: CON-0001
title: "Login API"
type: api
format: openapi
spec: SPEC-0001
version: 1.0.0
status: active
artifact: "contracts/api/login.openapi.yaml"
tests: [TST-0001]
---

# Contract: Login API

> **Spec:** SPEC-0001 · **Typ:** API (OpenAPI 3.1) · **Status:** active

## Zweck

Dieser Contract beschreibt das HTTP-Interface für die Login-Funktionalität gemäß FR-01 bis FR-04 in SPEC-0001. Implementierungen MÜSSEN das im Artifact hinterlegte OpenAPI-Schema einhalten.

## Geltungsbereich

- **In Scope:** Request-/Response-Schemas, Status-Codes, Header für `POST /v1/auth/login`
- **Out of Scope:** Authentifizierungs-Logik selbst (das ist Implementierungsdetail), Refresh-Token-Endpoint (CON-XXXX)

## Verbindlichkeit

1. Jeder Request gegen `/v1/auth/login` MUSS dem Schema entsprechen.
2. Jede Response MUSS dem für den jeweiligen Status-Code definierten Schema entsprechen.
3. Breaking Changes (z.B. Pflichtfeld hinzufügen, Feld entfernen) erfordern MAJOR-Bump und ADR.
4. Schemathesis-basierter Contract-Test (TST-0001) MUSS in CI grün sein.

## Versionierung

- **1.0.0** (current) – Initiale Veröffentlichung
