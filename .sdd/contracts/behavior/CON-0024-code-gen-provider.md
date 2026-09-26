---
id: CON-0024
project: PRJ-0001
title: "CodeGenProvider-Interface und Implementierungen"
type: behavior
format: markdown
spec: SPEC-0008
version: 0.1.0
status: deprecated
artifact: "tool/sdd_cli/llm/"
tests: ["TST-0028", "TST-0030"]
deprecated_reason: "CodeGen-Pfad entfernt; Rollen nutzen get_role_provider (SPEC-0062)"
---

# Contract: CodeGenProvider-Interface und Implementierungen

> **Spec:** SPEC-0008 · **Typ:** Verhalten · **Status:** draft

## Zweck

Spezifiziert das `CodeGenProvider`-Protocol und alle Implementierungen, die es
erfüllen. Dieser Contract gilt ausschließlich für den **Orchestrator**.

Der `CodeGenProvider` unterscheidet sich fundamental vom `CompletionProvider`:
Er schreibt Dateien direkt in einen Workspace und gibt eine Liste der
tatsächlich erzeugten/veränderten Dateien zurück — nicht nur Text.

## Protokoll-Definition

```python
@runtime_checkable
class CodeGenProvider(Protocol):
    def generate(
        self,
        prompt: str,
        workspace: Path,
        *,
        timeout: int = 600,
        on_proc: Callable[[Any], None] | None = None,
    ) -> tuple[list[dict[str, Any]], str]: ...
```

- `prompt`: vollständiger Code-Generierungs-Prompt (Spec + Contracts + Fehlerkontext)
- `workspace`: absoluter Pfad zum Projekt-Root (Dateien werden relativ dazu geschrieben)
- `timeout`: maximale Laufzeit in Sekunden; bei Überschreitung → `RuntimeError`
- `on_proc`: optionaler Callback mit dem laufenden Prozess (nur für `ClaudeCliCodeGenProvider`)
- Rückgabe: `([{"path": "rel/path", "content": "..."}], explanation)`
  - `files`: Liste aller im Workspace neu erstellten oder veränderten Dateien
  - `explanation`: ein-zeilige Erklärung der generierten Änderungen (max. 200 Zeichen)

## Garantien

### G-01: ClaudeCliCodeGenProvider

- Sucht `claude` via `shutil.which`; fehlt es → `RuntimeError("claude CLI nicht gefunden")`
- Ruft `claude --print --dangerously-skip-permissions -p <prompt>` als Subprocess auf
- `on_proc`-Callback erhält das `subprocess.Popen`-Objekt nach dem Start
- Entdeckt erzeugte/veränderte Dateien via `git diff --name-only` + `git ls-files --others`
- Gibt die Datei-Inhalte als Liste zurück (nicht nur Pfade)
- Bei Timeout: Prozess wird mit `proc.kill()` beendet → `RuntimeError`

### G-02: OpenAICompatCodeGenProvider

- Lazy-importiert `openai`; fehlt das Paket → `RuntimeError("... pip install 'sdd-cli[lm-studio]'")`
- Sendet Prompt mit expliziter JSON-Schema-Anforderung:
  ```
  Return ONLY a JSON object:
  {"files":[{"path":"relative/path","content":"..."}],"explanation":"..."}
  ```
- Extrahiert erstes `{...}`-JSON-Objekt aus der Antwort (robustes Parsing)
- Schreibt jede Datei aus `files` in `workspace / path` (erstellt Verzeichnisse)
- `on_proc`-Callback wird **nicht** aufgerufen (kein Subprocess)
- `explanation` = Wert aus JSON-Antwort; fehlt er → `f"implement via openai-compat"`

### G-03: Factory-Auflösung

`get_code_gen_provider(config)` löst in dieser Reihenfolge auf:

```
config.raw["llm"]["orchestrator"]      (Komponenten-Override)
  ↓ fehlt?
config.raw["llm"]["code_gen"]          (globaler Code-Gen-Default)
  ↓ fehlt?
Built-in-Default: ClaudeCliCodeGenProvider
```

### G-04: Erlaubte Provider-Werte (CodeGenProvider)

`claude-cli`, `openai-compat`. Jeder andere Wert → `ValueError` mit Liste der
erlaubten Werte.

### G-05: Workspace-Integrität

- `ClaudeCliCodeGenProvider` schreibt Dateien direkt (Claude hat `--dangerously-skip-permissions`)
- `OpenAICompatCodeGenProvider` schreibt ausschließlich Dateien, deren `path` nicht mit `.sdd/`, `specs/`, `contracts/`, `tests/` beginnt (Schutz vor Überschreiben von SDD-Artefakten)
- Beide Provider schreiben **nicht** außerhalb von `workspace`; ein relativer Pfad der mit `../` beginnt → `ValueError`

### G-06: Fehler-Propagation

- Beide Provider propagieren unerwartete Exceptions unverändert an den Orchestrator
- Der Orchestrator fängt diese ab und löst bei Bedarf Retry-Logik aus (CON-0012)

## Invarianten

- **INV-01:** `generate()` schreibt immer Dateien auf Disk, bevor es zurückgibt — der Rückgabewert reflektiert den tatsächlichen Disk-Zustand.
- **INV-02:** `generate()` liest keine Dateien aus `.sdd/holdout/` (CON-0009 INV-01 gilt auch für den Provider).
- **INV-03:** Kein `openai`-Import auf Modul-Ebene; ausschließlich lazy import im Konstruktor.
- **INV-04:** `on_proc` wird bei `OpenAICompatCodeGenProvider` ignoriert, aber die Signatur akzeptiert ihn (LSP).

## Begriffe

| Begriff                      | Definition                                                       |
|------------------------------|------------------------------------------------------------------|
| `CodeGenProvider`            | `typing.Protocol` für agentische Datei-Generierung              |
| Workspace                    | Absoluter Pfad zum Projekt-Root; Dateipfade werden relativ dazu  |
| `--dangerously-skip-permissions` | Claude CLI-Flag das Datei-Schreiben ohne Bestätigung erlaubt |
| SDD-Artefakte                | Dateien in `specs/`, `contracts/`, `tests/`, `.sdd/`            |
