---
id: CON-0078
title: "remote-api-slo"
type: performance
format: slo-yaml
spec: SPEC-0023
version: 0.1.0
status: draft
tests: [TST-0109]
---

# Contract: Remote API SLO

> **Spec:** SPEC-0023 · **Typ:** Performance (SLO) · **Status:** draft

## Zweck

Definiert die Latenz-SLOs für die Remote-Control-Endpoints — maßgeblich für die
Wahrnehmung auf dem mobilen Client via Tailscale/VPN.

## Service Level Objectives

| SLI | Ziel | Messfenster | Konsequenz |
|---|---|---|---|
| `/ws/chat` — erstes Token nach Senden (gemockt, ohne LLM-Latenz) | < 200 ms | 10 Messungen | Test-Failure |
| `/api/sdd/run` — erste SSE-Zeile nach Request | < 1000 ms | 10 Messungen | Test-Failure |
| `/api/push/subscribe` — Response-Zeit | < 100 ms | 20 Messungen | Test-Failure |
| PushStore.broadcast — Zeit bis alle Subscriptions benachrichtigt (1 Subscription, gemockt) | < 500 ms | 5 Messungen | Warnung |

## Messung

- **`/ws/chat`:** Zeit von Verbindungsaufbau bis zum ersten `{"delta": "..."}`. LLM-Aufruf
  ist gemockt — es wird die Zeit der Intent-Prüfung + Frame-Routing gemessen.
- **`/api/sdd/run`:** Zeit von POST-Request bis zur ersten `data:`-Zeile im SSE-Stream.
  Subprocess wird gemockt (sofortiger Output).
- **`/api/push/subscribe`:** Reine In-Memory-Operation, ohne Netzwerkaufruf.
- **Abgrenzung:** Tailscale/VPN-Netzwerklatenz ist explizit ausgeschlossen.

## Rationale

- 200ms für erstes Chat-Token: subjektiv als "sofort" wahrgenommen, deckt
  WebSocket-Handshake + Intent-Parse + erstes Claude-Token ab.
- 1000ms für erste SSE-Zeile: `sdd`-Startup-Zeit variiert je nach Command.
  Subprocess-Start selbst dauert ~50-200ms.
- 100ms für Push-Subscribe: reine In-Memory-Operation ohne externe Calls.
