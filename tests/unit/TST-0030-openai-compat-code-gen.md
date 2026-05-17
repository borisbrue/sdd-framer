---
id: TST-0030
project: PRJ-0001
title: "OpenAICompatCodeGenProvider Unit-Tests"
level: unit
spec: SPEC-0008
contract: CON-0024
status: planned
framework: pytest
artifact: "tests/unit/test_llm_providers.py"
tags: ["llm", "openai-compat", "code-gen", "orchestrator", "mock"]
---

# Test: OpenAICompatCodeGenProvider Unit-Tests

> **Spec:** SPEC-0008 · **Level:** Unit · **Contract:** CON-0024

## Zweck

Prüft `OpenAICompatCodeGenProvider.generate()`: korrekte JSON-Extraktion aus der
LLM-Antwort, Datei-Schreiben in den Workspace, Schutz vor SDD-Artefakt-Überschreibung
und Fehlerbehandlung — vollständig ohne echte LLM-Verbindung (tmp-Verzeichnis + Mock).

## Test Cases

| TC    | Was wird geprüft?                                                                     |
|-------|---------------------------------------------------------------------------------------|
| TC-01 | Valide JSON-Antwort `{"files":[...],"explanation":"..."}` → Dateien auf Disk geschrieben |
| TC-02 | Mehrere Dateien in der Antwort → alle werden korrekt in `workspace` erzeugt          |
| TC-03 | Verschachtelte Pfade werden angelegt (`workspace / "a/b/c.py"` → `mkdir -p`)         |
| TC-04 | `explanation` aus JSON-Antwort wird als zweiter Rückgabewert übergeben               |
| TC-05 | JSON eingebettet in Prosa-Text → `{...}`-Block wird korrekt extrahiert               |
| TC-06 | Ungültiges JSON in LLM-Antwort → `json.JSONDecodeError` wird propagiert              |
| TC-07 | Pfad beginnt mit `specs/` → `ValueError` (SDD-Artefakt-Schutz, CON-0024 G-05)       |
| TC-08 | Pfad beginnt mit `../` → `ValueError` (Workspace-Escape-Schutz)                     |
| TC-09 | `on_proc`-Callback wird ignoriert (kein Subprocess)                                  |
| TC-10 | Timeout-Parameter wird an `openai`-Aufruf weitergereicht (via `httpx`-Timeout-Config)|
| TC-11 | Fehlendes `openai`-Paket → `RuntimeError` mit `"lm-studio"` im Text                  |
| TC-12 | `isinstance(provider, CodeGenProvider)` → `True`                                     |

## Ausführung

```bash
pytest tests/unit/test_openai_compat_code_gen.py -v
```
