---
id: CON-0086
title: "rotate-token API"
type: api
format: openapi
spec: SPEC-0025
version: 0.2.0
status: draft
tests: [TST-0096]
---

# Contract: rotate-token API

> **Spec:** SPEC-0025 · **Typ:** API · **Status:** draft

## Zweck

POST /api/auth/rotate-token verifiziert den alten Token, generiert einen neuen
und invalidiert den alten sofort in der In-Memory-Blacklist.

> **0.2.0 (2026-09-10):** INV-03 nannte `config.yaml` als Ziel. Die Datei ist
> versioniert; der Token ist die Bearer-Credential fuer `POST /api/remote/run`.
> Jede Rotation schrieb den neuen Wert genau dorthin zurueck, wo der alte das
> Problem war (#103). Ziel ist jetzt die gitignorte lokale Ergaenzung, die
> `load_config` ueber config.yaml legt. Atomaritaet und alle Garantien bleiben.

## Invarianten

| ID | Invariante |
|---|---|
| INV-01 | Threading-Lock verhindert doppelte Rotation bei parallelen Requests |
| INV-02 | Alter Token wird IMMER blacklistet wenn ein neuer erfolgreich geschrieben wurde |
| INV-03 | Der Token wird nach `.sdd/config.local.yaml` geschrieben (gitignored, Rechte 0600), atomar via tempfile + os.replace. `.sdd/config.yaml` bleibt unberuehrt. |

## Garantien

| ID | Garantie |
|---|---|
| G-01 | HTTP 401 ohne Authorization-Header |
| G-02 | Neuer Token = secrets.token_hex(32) → 64 Hex-Zeichen |
| G-03 | Alter Token landet sofort in der In-Memory-Blacklist |
| G-04 | HTTP 401 wenn Token nicht mit aktuellem übereinstimmt |
| G-05 | HTTP 401 wenn Token bereits blacklistet ist |
| G-06 | Response: {token: newToken} |

## Endpoint

```
POST /api/auth/rotate-token
Authorization: Bearer <current_token>
Response 200: { token: string }  # 64-char hex
Response 401: { detail: "invalid_token" }
```
