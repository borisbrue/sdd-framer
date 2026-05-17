---
id: CON-0089
title: "token-rotation-slo"
type: performance
format: slo-yaml
spec: SPEC-0025
version: 0.1.0
status: draft
tests: [TST-0099]
---

# Contract: Token-Rotation SLO

> **Spec:** SPEC-0025 · **Typ:** Performance (SLO) · **Status:** draft

## Service Level Objectives

| SLI | Ziel | Messfenster | Konsequenz |
|---|---|---|---|
| GET /api/server-info p95-Latenz | < 100 ms | 20 Messungen | Test-Failure |
| POST /api/auth/rotate-token p95-Latenz | < 500 ms | 10 Messungen | Test-Failure |

## Messung

- **server-info:** Kein File-I/O, reine In-Memory-Operation → p95 muss weit
  unter 100 ms bleiben.
- **rotate-token:** Beinhaltet atomares Schreiben der config.yaml via tempfile
  + os.replace. 500 ms ist ein konservativer Grenzwert für lokalen Dateisystem-I/O.
- **Messmethode:** FastAPI TestClient (In-Process), `time.monotonic()` vor/nach
  dem Request.
