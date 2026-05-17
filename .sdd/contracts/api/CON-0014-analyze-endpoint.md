---
id: CON-0014
project: ""
title: "POST /api/docs/{id}/analyze – Dokument-Analyse-Endpoint"
type: api
format: openapi
spec: SPEC-0005
version: 0.1.0
status: active
artifact: ""
tests: ["TST-0013"]
---

# Contract: POST /api/docs/{id}/analyze

> **Spec:** SPEC-0005 · **Typ:** API (OpenAPI) · **Status:** draft

## Zweck

REST-Endpoint der sdd-web-api, der ein Spec- oder Contract-Dokument analysiert
und kontextsensitive Nachfragen zurückgibt. Ruft intern den Claude Code CLI
Subprocess auf (CON-0013).

## Request

```
PUT /api/docs/{id}/analyze
Content-Type: application/json
```

```json
{
  "content": "<vollständiger Markdown-Text des Dokuments>",
  "doc_type": "spec | contract",
  "session_id": "<uuid>",
  "answered_questions": [
    { "id": "q1", "answer": "Der Nutzer sieht eine Inline-Fehlermeldung." }
  ]
}
```

| Feld                | Typ      | Pflicht | Beschreibung                                         |
|---------------------|----------|---------|------------------------------------------------------|
| `content`           | string   | ja      | Aktueller Dokumentinhalt (Markdown + Frontmatter)    |
| `doc_type`          | enum     | ja      | `spec` oder `contract`                               |
| `session_id`        | string   | nein    | UUID für Session-Tracking; wird neu erstellt wenn leer |
| `answered_questions`| array    | nein    | Bereits beantwortete Fragen (verhindert Wiederholung) |

## Response

### 200 OK

```json
{
  "session_id": "<uuid>",
  "questions": [
    {
      "id": "q1",
      "section": "Erfolgskriterien",
      "text": "Was passiert, wenn der Nutzer das Formular ohne Titel abschickt?",
      "severity": "error"
    }
  ],
  "issues": [
    {
      "section": "User Stories",
      "text": "US-02 hat kein messbares Erfolgskriterium.",
      "severity": "warning"
    }
  ],
  "suggestions": [
    {
      "text": "Für Gherkin-Contracts: Füge einen Szenario-Outline für Randfälle hinzu."
    }
  ]
}
```

### 503 Service Unavailable — Claude Code CLI nicht gefunden

```json
{
  "error": "claude_not_found",
  "message": "Claude Code CLI nicht gefunden. Installiere Claude Code und melde dich an.",
  "install_url": "https://claude.ai/code"
}
```

### 504 Gateway Timeout — Claude Code CLI-Aufruf überschreitet Timeout

```json
{ "error": "claude_timeout", "message": "Analyse hat das Zeitlimit (30 s) überschritten." }
```

### 502 Bad Gateway — Claude-Response kein valides JSON

```json
{ "error": "claude_parse_error", "message": "...", "raw": "<erster 500 Zeichen>" }
```

## Severity-Werte

| Wert         | Bedeutung                                             |
|--------------|-------------------------------------------------------|
| `error`      | Dokument ist unvollständig / verletzt eine SDD-Regel  |
| `warning`    | Empfohlene Ergänzung, kein Blockierer                 |
| `suggestion` | Optionaler Verbesserungsvorschlag                     |

## Invarianten

- **INV-01:** `questions` enthält maximal 5 Einträge pro Response.
- **INV-02:** Jede Question hat eine eindeutige `id` (stabil über mehrere Aufrufe mit gleichem Inhalt).
- **INV-03:** `answered_questions` aus dem Request erscheinen nie in der Response.
- **INV-04:** `session_id` im Response ist immer gesetzt (neu generiert oder weitergegeben).
