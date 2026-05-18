---
id: CON-0094
title: "pwa-dashboard-slo"
type: performance
format: slo-yaml
spec: SPEC-0024
version: 0.1.0
status: draft
tests: [TST-0104]
---

# Contract: PWA Dashboard SLO

> **Spec:** SPEC-0024 · **Typ:** Performance (SLO) · **Status:** draft

## Zweck

Definiert die Performance-Anforderungen für GET /api/specs — das zentrale
Polling-Endpoint des Dashboard-Tabs. Der p95-Grenzwert stellt sicher, dass
das 10-Sekunden-Polling-Intervall nicht durch langsame Server-Antworten
dominiert wird.

## Service Level Objectives

| SLI | Ziel | Messfenster | Konsequenz |
|---|---|---|---|
| GET /api/specs p95-Antwortzeit | < 200 ms | 20 Messungen | Test-Failure |
| GET /api/specs maximale Antwortzeit | < 1000 ms | Einzelmessung | Warning |
| Polling-Intervall Dashboard-Tab | 10 Sekunden | Konfiguriert in DashboardTab | Anforderung |

## Messung

- **Messmethode:** FastAPI TestClient (In-Process), `time.monotonic()` vor/nach Request.
- **Voraussetzung:** Mindestens ein SDD-Projekt mit Specs im `_root`.
- **Abgrenzung:** Netzwerklatenz (Tailscale/VPN) ist explizit ausgeschlossen —
  nur Server-seitige Verarbeitungszeit wird gemessen.
- **Begründung 200ms:** Bei 10s-Polling-Intervall verursacht eine 200ms-Antwort
  nur 2 % Overhead. Über 200ms würde bei schwacher Serverlast merklich auffallen.

## Polling-Verhalten (Frontend)

- Polling startet beim Öffnen des Dashboard-Tabs
- Polling stoppt beim Verlassen des Dashboard-Tabs (cleanup)
- Bei Polling-Fehler (Netzwerk): kein sofortiger Retry — nächster Zyklus in 10s. Der ApiClient setzt ConnectionStore → `disconnected` (CON-0090 G-08). Das 10s-Intervall ist die maßgebliche Retry-Zeit. (CF-0024-017 resolved)
- Bei HTTP 401: Polling stoppt, ApiClient löscht gesamten `sdd_config`-Key (CON-0090 G-02), ConnectionStore → `setup_required` (CF-0024-018 resolved)
