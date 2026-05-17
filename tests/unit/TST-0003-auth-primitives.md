---
id: TST-0003
title: "Unit: Password-Hashing und Token-Generierung"
level: unit
spec: SPEC-0001
contract: CON-0001
status: planned
framework: pytest
artifact: "tests/unit/test_auth_primitives.py"
tags: [auth, unit, crypto]
---

# Test: Unit Password-Hashing und Token-Generierung

> **Level:** unit · **Spec:** SPEC-0001 · **Contract:** CON-0001

## Was wird geprüft?

Isolierte Tests der kryptografischen Primitives:

1. Argon2id-Wrapper hasht und verifiziert korrekt
2. JWT-Generator erzeugt korrekt strukturierte ES256-Token mit erwarteten Claims
3. Refresh-Token sind kryptografisch zufällig und ausreichend lang (≥ 256 Bit Entropie)

## Vorbedingungen

- Keine — reine In-Process-Tests ohne externe Abhängigkeiten
- Test-Keypair für ES256 als Fixture

## Ablauf

1. `hash_password(plain)` → Hash zurückgeben, der mit `verify_password(plain, hash)` validiert
2. `verify_password(plain, hash)` schlägt bei falschem Passwort fehl
3. `generate_access_token(user_id)` → JWT mit `iss`, `sub`, `iat`, `exp`, `alg=ES256`
4. `generate_refresh_token()` → 32-Byte zufällig, Base64URL-kodiert
5. Zwei aufeinanderfolgende Refresh-Token sind unterschiedlich

## Erwartetes Ergebnis

Alle Assertions grün. Argon2id-Parameter entsprechen Empfehlung (m=64MB, t=3, p=4 oder besser).

## Negativfälle

- `verify_password("falsch", hash)` → False
- `verify_password("plain", "kaputt")` → False, keine Exception nach außen
- Token-Generierung ohne Keypair → Klare Exception

## Verknüpfung mit Contract

Dieser Test stützt die nicht-funktionalen Anforderungen aus SPEC-0001 §5 (Security: Argon2id, JWT ES256), nicht direkt das API-Schema.

## Hinweise zur Implementierung

```python
# tests/unit/test_auth_primitives.py
import pytest
from auth.primitives import hash_password, verify_password, generate_access_token

def test_hash_and_verify_roundtrip():
    h = hash_password("Correct-Horse-Battery")
    assert verify_password("Correct-Horse-Battery", h)
    assert not verify_password("wrong", h)
```
