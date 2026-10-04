---
id: CON-0074
title: "ws-chat"
type: api
format: openapi
spec: SPEC-0023
version: 0.2.0
status: draft
tests: [TST-0105]
---

# Contract: WebSocket /ws/chat

> **Spec:** SPEC-0023 · **Typ:** API · **Status:** draft

## Zweck

WebSocket-Endpoint für den Chat-Tab der PWA. Der Nutzer sendet Textnachrichten,
Claude antwortet mit Streaming-Tokens. Erkannte SDD-Intents werden automatisch
als Commands ausgeführt — der Output erscheint als `command_output`-Frames vor
der Claude-Antwort.

## Garantien

| ID | Garantie |
|---|---|
| G-01 | Auth: Bearer-Token im ersten JSON-Frame `{"auth": "<token>"}` oder HTTP-Header `Authorization: Bearer`. Fehlt → WebSocket wird mit Code 4001 geschlossen |
| G-02 | Eingehend: `{"text": "..."}` — jede andere Struktur wird ignoriert |
| G-03 | Streaming-Token: `{"delta": "..."}` — eines pro Token, leer-String möglich |
| G-04 | Command-Output-Frame: `{"type": "command_output", "line": "..."}` — eine Zeile pro Frame, erscheint vor der Claude-Antwort |
| G-05 | Abschluss-Frame: `{"type": "done"}` — einmal am Ende jeder Antwort |
| G-06 | IntentParser läuft vor Claude: erkannter Intent → Command ausführen → Output als G-04-Frames → danach Claude-Antwort als G-03-Frames |
| G-07 | Nicht erkannte Nachricht → direkt an Claude, kein Command ausgeführt |
| G-08 | Chat-Kontext: letzte 20 Nachrichten der Session werden an Claude übergeben |
| G-09 | System-Prompt: Claude agiert als SDD-Assistent, kennt alle sdd-CLI-Commands |

## Intents (IntentParser)

> **v0.2.0 (2026-10-04, #128):** Die Intents `dev build`, `dev up` und `dev down` sind entfernt.
> Sie riefen die seit SPEC-0044 entfernte `sdd dev`-Gruppe auf, und der Chat lieferte nur die
> click-Fehlermeldung. Jeder Intent zeigt auf einen existierenden Befehl. `orchestrate` ist
> ein Adapter auf `sdd pipeline run SPEC --auto` (CON-0216 INV-05); TST-0105 prüft das.

| Muster | Command |
|---|---|
| `orchestrate <SPEC-ID>` | `sdd orchestrate --spec <SPEC-ID>` |
| `start <SPEC-ID>` | `sdd start <SPEC-ID>` |
| `status` | `sdd validate` |

## Endpoint

```
WS /ws/chat
Auth: Bearer im ersten Frame {"auth": "..."} oder HTTP-Header
Frame → Client: {"delta": "..."} | {"type": "command_output", "line": "..."} | {"type": "done"}
Frame ← Client: {"text": "..."}
Close 4001: invalid_token
```
