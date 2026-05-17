---
id: TST-0001
title: "OpenAPI-Konformität Login-Endpoint"
level: contract
spec: SPEC-0001
contract: CON-0001
status: planned
framework: schemathesis
artifact: "tests/contract/test_login_openapi.py"
tags: [auth, contract]
---

# Test: OpenAPI-Konformität Login-Endpoint

> **Level:** contract · **Spec:** SPEC-0001 · **Contract:** CON-0001

## Was wird geprüft?

Die laufende Implementierung verhält sich an `POST /v1/auth/login` exakt so, wie in `contracts/api/login.openapi.yaml` beschrieben: gültige Request-Bodies werden akzeptiert, ungültige zurückgewiesen, alle Status-Codes und Response-Schemas stimmen.

## Vorbedingungen

- Service läuft unter Test-URL
- Mindestens ein Test-Account existiert
- Datenbank in bekanntem Ausgangszustand (Fixture)

## Ablauf

1. Schemathesis lädt `contracts/api/login.openapi.yaml`
2. Fuzzing: generiert valide und invalide Requests gemäß Schema
3. Sendet Requests gegen die laufende API
4. Prüft jede Response gegen das Schema (Status, Header, Body)
5. Stateful Testing: prüft, dass Token tatsächlich nutzbar ist

## Erwartetes Ergebnis

- 0 Schema-Verletzungen
- Alle dokumentierten Status-Codes werden erreicht (200, 400, 401, 423)
- Keine undokumentierten 5xx-Antworten

## Negativfälle

- Server-Crash bei extremen Inputs → Fail
- Antworten, die nicht im Schema stehen → Fail
- Felder im Response, die nicht im Schema deklariert sind → Fail (additionalProperties: false)

## Verknüpfung mit Contract

Dieser Test prüft konkret folgende Punkte aus CON-0001:

- [x] LoginRequest-Schema wird durchgesetzt
- [x] LoginResponse-Schema wird durchgesetzt
- [x] Status-Codes 200/400/401/423 entsprechen ihren Schemas
- [x] `additionalProperties: false` wird respektiert

## Hinweise zur Implementierung

```python
# tests/contract/test_login_openapi.py
import schemathesis

schema = schemathesis.from_path("contracts/api/login.openapi.yaml")

@schema.parametrize()
def test_api(case):
    case.call_and_validate()
```

Pre-Condition im Test-Setup: Test-Account `alice@example.com` mit Passwort aus Vault.
