---
id: CON-0013
project: ""
title: "Analyzer – Claude Code CLI Subprocess und Session-Verwaltung"
type: behavior
format: markdown
spec: SPEC-0005
version: 0.4.0
status: active
artifact: ""
tests: ["TST-0013"]
---

# Contract: Analyzer – Claude Code CLI Subprocess und Session-Verwaltung

> **Spec:** SPEC-0005 · **Typ:** Verhalten · **Status:** active

## Änderungshistorie

| Version | Änderung |
|---------|----------|
| 0.1.0 | Initialer Entwurf: Claude Code CLI Subprocess |
| 0.2.0 | Umstieg auf anthropic SDK (temporär) |
| 0.3.0 | Rückkehr zum Subprocess-Ansatz gemäß SPEC-0005 §3.1 |
| 0.4.0 | G-03: Markdown-Code-Fence-Handling vor JSON-Extraktion |

## Zweck

Dieser Contract definiert das Verhalten von `tool/sdd_cli/web/api/analyzer.py`: wie
`claude` als Subprocess aufgerufen wird, wie Sessions verwaltet werden und
wie Prompts aufgebaut sind.

## Garantien

### G-01: Claude Code CLI-Aufruf

```bash
claude --print --output-format json -p "<ANALYSIS_PROMPT>"
```

- `claude` wird via `shutil.which("claude")` im PATH gesucht
- Timeout: 120 Sekunden (`subprocess.run(..., timeout=120)`)
- Kein eigener `ANTHROPIC_API_KEY` nötig — bestehende Claude Code
  Authentifizierung des Users wird genutzt

### G-02: Fehlschlag wenn `claude` nicht im PATH

Ist `claude` nicht im PATH (`shutil.which` → `None`): HTTP 503 mit:
```json
{
  "error": "claude_not_found",
  "message": "Claude Code CLI nicht gefunden. Installiere Claude Code und melde dich an.",
  "install_url": "https://claude.ai/code"
}
```

### G-03: Response-Parsing

`claude --output-format json` liefert einen Wrapper:
```json
{
  "type": "result",
  "result": "<claude-text-output>",
  "total_cost_usd": 0.001
}
```

Das innere `result`-Feld wird in zwei Schritten auf das JSON-Nutzobjekt reduziert:

1. **Markdown-Code-Fence entfernen:** Enthält `result` einen Codeblock der Form
   `` ```json\n{...}\n``` ``, wird der Inhalt zwischen den Backticks extrahiert
   (regulärer Ausdruck ````(?:json)?\s*(\{.*\})\s*````, DOTALL). Dieser Schritt
   fängt das häufige Verhalten ab, bei dem Claude JSON in einen Codeblock einbettet.
2. **Fallback:** Kein Codeblock vorhanden → erstes `{` bis letztes `}` extrahieren.

Schlägt das Parsen fehl: HTTP 502 mit:
```json
{ "error": "claude_parse_error", "message": "...", "raw": "<erste 500 Zeichen>" }
```

### G-04: Prompt-Struktur

Der `-p`-Prompt enthält in dieser Reihenfolge:
1. Prompt-Template (`spec-prompt.md` oder `contract-prompt.md`) mit:
   - Rolle & Aufgabe
   - Bereits beantwortete Fragen (verhindert Wiederholung)
   - Dokument-Inhalt (vollständiges Markdown inkl. Frontmatter)
   - Output-Format-Anweisung

### G-05: Maximale Fragen

Pro Aufruf werden maximal **5 Fragen** zurückgegeben. Bereits beantwortete
Fragen (erkannt über `id`) werden serverseitig herausgefiltert, bevor die
Response zurückgegeben wird.

### G-06: Prompt-Templates

Templates liegen in `.sdd/templates/analysis/`:
- `spec-prompt.md` — Platzhalter: `{{document_content}}`, `{{answered_context}}`
- `contract-prompt.md` — gleiche Platzhalter

Fehlt ein Template, wird ein eingebettetes Fallback verwendet (kein Absturz).

## Invarianten

- **INV-01:** Sessions liegen in-memory; TTL = 1 Stunde seit letzter Nutzung.
- **INV-02:** Eine Session gehört zu genau einem `doc_id`.
- **INV-03:** `content` wird auf 50 000 Zeichen gekürzt bevor er in den Prompt geht.
- **INV-04:** `answered_questions` aus dem Request erscheinen nie in der Response.

## Begriffe

| Begriff          | Definition                                                          |
|------------------|---------------------------------------------------------------------|
| Session          | In-memory-Objekt pro `session_id`; akkumuliert beantwortete Fragen |
| Prompt-Template  | Markdown-Datei mit `{{...}}`-Platzhaltern in `.sdd/templates/analysis/` |
| Fallback-Template| Eingebettetes Template in `analyzer.py`, falls Datei fehlt         |
