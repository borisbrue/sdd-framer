---
id: SPEC-0008
title: Pluggable LLM-Provider – SOLID-Abstraktionsschicht für alle KI-Komponenten
status: implemented
owner: Boris
created: 2026-05-12
updated: 2026-05-13
version: 0.6.0
priority: high
tags:
- llm
- provider-pattern
- solid
- lm-studio
- evaluator
- orchestrator
- analyzer
- refactoring
depends_on:
- SPEC-0004
- SPEC-0005
contracts:
- CON-0022
- CON-0023
- CON-0024
tests:
- TST-0028
- TST-0029
- TST-0030
- TST-0031
- TST-0032
- TST-0033
- TST-0034
- TST-0035
- TST-0036
adrs: []
---
# Pluggable LLM-Provider – SOLID-Abstraktionsschicht für alle KI-Komponenten

> **Status:** draft · **Owner:** Boris · **Version:** 0.6.0

## 1. Kontext & Motivation

Das Projekt enthält vier Integrationspunkte, die LLMs direkt und hart gekoppelt
nutzen:

| Komponente       | Datei                           | Aktueller Ansatz               | Verwendungszweck                         |
|------------------|---------------------------------|--------------------------------|------------------------------------------|
| **Evaluator**    | `tool/sdd_cli/evaluator.py`     | `anthropic` SDK, Haiku         | HOL-Szenario planen + bewerten           |
| **Orchestrator** | `tool/sdd_cli/orchestrator.py`  | `claude` CLI Subprocess        | Agentische Code-Generierung (Datei-Schreiben) |
| **Analyzer**     | `web/api/analyzer.py`           | `claude` CLI Subprocess        | Spec/Contract-Analyse → strukturiertes JSON |
| **AI-Routes**    | `web/api/routes/ai.py`          | `anthropic` SDK, Opus          | Spec-Generierung, -Verbesserung, Contract-Vorschläge |

Alle vier Integrationspunkte haben dasselbe strukturelle Problem:
- **Konkrete Abhängigkeit** auf eine einzelne LLM-Implementierung
- **Keine Austauschbarkeit** ohne Code-Änderung
- **Keine Testbarkeit** ohne echte API-Calls oder CLI-Instanz
- **Kein Privacy-Modus** (alle Daten gehen in die Cloud)

Ziel ist eine **SOLID-konforme Provider-Abstraktionsschicht** im Backend, die:
1. LM Studio und andere OpenAI-kompatible lokale Dienste als Alternative ermöglicht
2. Den bestehenden Code durch Dependency Inversion entkoppelt
3. Über `.sdd/config.yaml` ohne Code-Änderung konfigurierbar ist
4. Vollständig unit-testbar ist (Provider mockbar)

## 2. Zielsetzung

**Primärziel:**
Eine einheitliche, SOLID-konforme Provider-Abstraktionsschicht, die alle vier
LLM-Integrationspunkte bedient und ohne Code-Änderung zwischen Cloud- und
lokalen LLM-Backends wechselbar macht.

**Erfolgskriterien (messbar):**
- [ ] Alle vier Komponenten nutzen ausschließlich Provider-Interfaces, keine direkten SDK-Imports
- [ ] `provider: openai-compat` funktioniert für Evaluator, Analyzer und AI-Routes
- [ ] `provider: openai-compat` funktioniert für den Orchestrator (JSON-basierte Code-Gen)
- [ ] Kein `ANTHROPIC_API_KEY` erforderlich bei vollständiger `openai-compat`-Konfiguration
- [ ] Bestehende `anthropic`/`claude-cli` Defaults bleiben vollständig erhalten (kein Breaking Change)
- [ ] Alle Provider-Implementierungen sind ohne echte LLM-Verbindung testbar (via Mock)

**Nicht-Ziele (explizit):**
- Streaming-Unterstützung (alle Komponenten nutzen Single-Request/Response)
- Automatisches Model-Discovery oder Health-Checks
- Unterstützung proprietärer lokaler Server-Protokolle jenseits OpenAI-compat
- Neue UI-Features für Provider-Auswahl (rein backend-seitig)

## 3. SOLID-Analyse der aktuellen Architektur

| Prinzip | Verletzung (Ist-Zustand)                                              |
|---------|-----------------------------------------------------------------------|
| **S**   | `evaluator.py` enthält LLM-Logik, HTTP-Ausführung und Bewertung gemischt |
| **O**   | Neues LLM-Backend erfordert Änderung in jeder der vier Dateien        |
| **L**   | Kein gemeinsamer Typ — die vier Integrationspunkte sind nicht austauschbar |
| **I**   | Ein universeller "LLM-Aufruf" würde einfache Completion und agentische Code-Gen mischen |
| **D**   | Evaluator, Orchestrator, Analyzer, AI-Routes hängen von Konkreta ab (`anthropic.Anthropic`, `subprocess`) |

## 4. Architektur

### 4.1 Zwei Protokoll-Interfaces (ISP + LSP)

Das Interface Segregation Principle erfordert zwei getrennte Interfaces, da
einfache Completion und agentische Code-Generierung fundamental unterschiedliche
Verträge haben:

```python
# tool/sdd_cli/llm/base.py

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol, Any, runtime_checkable
from pathlib import Path
from collections.abc import Callable


@dataclass
class UsageMetadata:
    """Token-Nutzungsdaten einer Completion; None-Felder wenn Provider sie nicht liefert."""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    model: str = ""


@dataclass
class CompletionResult:
    """Rückgabe von CompletionProvider.complete()."""
    text: str
    usage: UsageMetadata | None = None
    # usage ist None bei ClaudeCliCompletionProvider (CLI liefert keine Token-Counts).
    # Aufrufer die usage benötigen (ai.py → usage_store) prüfen auf None.


@runtime_checkable
class CompletionProvider(Protocol):
    """Synchrones Prompt → CompletionResult.

    Genutzt von: Evaluator, Analyzer, AI-Routes.
    Implementierungen: AnthropicCompletionProvider,
                       ClaudeCliCompletionProvider,
                       OpenAICompatCompletionProvider.
    """
    def complete(
        self,
        prompt: str,
        *,
        max_tokens: int = 512,
        system_prompt: str | None = None,
        timeout: int | None = None,
    ) -> CompletionResult: ...
    # timeout: Sekunden; None = kein Limit. Evaluator belegt ihn mit
    # timeout_per_scenario; andere Komponenten lassen None.


@runtime_checkable
class CodeGenProvider(Protocol):
    """Agentische Code-Generierung, die Dateien in einen Workspace schreibt.

    Genutzt von: Orchestrator.
    Implementierungen: ClaudeCliCodeGenProvider,
                       OpenAICompatCodeGenProvider.
    """
    def generate(
        self,
        prompt: str,
        workspace: Path,
        *,
        timeout: int = 600,
        on_proc: Callable[[Any], None] | None = None,
    ) -> tuple[list[dict[str, Any]], str]: ...
    # Returns: ([{"path": "...", "content": "..."}], explanation)
    #
    # Invariante: Die zurückgegebene Dateiliste spiegelt exakt wider, was nach
    # dem Lauf auf Disk in `workspace` liegt. Wie die Liste ermittelt wird,
    # ist implementierungsspezifisch:
    #   - ClaudeCliCodeGenProvider:      git diff --name-only nach dem Lauf
    #   - OpenAICompatCodeGenProvider:   aus dem eigenen Schreib-Log (welche
    #                                    Pfade wurden erfolgreich geschrieben)
    # `content` wird nach dem Schreiben von Disk gelesen — nicht direkt aus
    # der LLM-Antwort übergeben.
    #
    # `on_proc`: wird von nicht-CLI-Providern (OpenAICompatCodeGenProvider)
    # ignoriert und niemals aufgerufen. Aufrufer dürfen sich nicht darauf
    # verlassen, dass der Callback ausgelöst wird.
```

`CompletionProvider.complete()` gibt immer `CompletionResult` zurück — JSON-Parsing
aus `result.text` liegt in der Verantwortung des Aufrufers.

**Parameter- und Rückgabe-Verhalten je Provider:**

| Parameter / Rückgabe | `AnthropicCompletionProvider`                          | `OpenAICompatCompletionProvider`               | `ClaudeCliCompletionProvider`                |
|----------------------|--------------------------------------------------------|------------------------------------------------|----------------------------------------------|
| `max_tokens`         | An API übergeben                                       | An API übergeben                               | **Ignoriert** (CLI kennt kein `--max-tokens`)|
| `system_prompt`      | `system=[{"type":"text","text":..., "cache_control":{"type":"ephemeral"}}]` | `{"role":"system","content":...}` in messages | Als Präfix: `<system>\n...\n</system>\n\n{prompt}` |
| `timeout`            | `client.messages.create(..., timeout=timeout)`        | `client.chat.completions.create(..., timeout=timeout)` | `subprocess.run(timeout=timeout)`     |
| `temperature`        | Aus Config (Default `0.0`), an API übergeben          | Aus Config (Default `0.0`), an API übergeben   | **Ignoriert** (CLI bietet kein Temperatur-Flag) |
| `result.usage`       | Befüllt aus `response.usage` (Tokens + Cache-Hits)    | Befüllt aus `response.usage`                   | `None` (CLI liefert keine Token-Counts)      |

`temperature` ist kein Call-Parameter — er wird beim Provider-Aufbau aus der Config gelesen
und im Provider-Objekt gehalten. Default: `0.0`. Empfohlener Override für AI-Routes: `0.7`.

`ai.py` liest nach dem Refactor `result.usage` und ruft `usage_store.record_usage()` auf wenn
`result.usage is not None` — die bestehende Kostenverfolgung bleibt damit vollständig erhalten.
Prompt-Caching (`cache_control: ephemeral`) bleibt bei `AnthropicCompletionProvider` aktiv.

### 4.2 Provider-Implementierungen (OCP)

Neue Backends werden durch neue Klassen hinzugefügt, ohne bestehenden Code zu
ändern (Open/Closed Principle):

```
tool/sdd_cli/llm/
├── __init__.py          — Öffentliches API: get_completion_provider, get_code_gen_provider
├── base.py              — CompletionProvider, CodeGenProvider (Protocols)
├── factory.py           — Factory-Funktionen (Dependency Inversion)
└── providers/
    ├── __init__.py
    ├── anthropic.py     — AnthropicCompletionProvider
    ├── claude_cli.py    — ClaudeCliCompletionProvider, ClaudeCliCodeGenProvider
    └── openai_compat.py — OpenAICompatCompletionProvider, OpenAICompatCodeGenProvider
```

| Klasse                          | Interface           | Intern                                 |
|---------------------------------|---------------------|----------------------------------------|
| `AnthropicCompletionProvider`   | `CompletionProvider`| `anthropic.Anthropic()` SDK            |
| `ClaudeCliCompletionProvider`   | `CompletionProvider`| `claude --print --output-format json`  |
| `OpenAICompatCompletionProvider`| `CompletionProvider`| `openai.OpenAI(base_url=...)`          |
| `ClaudeCliCodeGenProvider`      | `CodeGenProvider`   | `claude --print --dangerously-skip-permissions` |
| `OpenAICompatCodeGenProvider`   | `CodeGenProvider`   | OpenAI-API → JSON `{files:[...]}` → schreibt selbst |

### 4.3 Factory-Funktionen (DIP)

Alle Komponenten erhalten ihren Provider über die Factory — keine direkte
Instantiierung von Provider-Klassen außerhalb von `factory.py`:

```python
# tool/sdd_cli/llm/factory.py

def get_completion_provider(
    config: SddConfig,
    component: Literal["evaluator", "analyzer", "ai_routes", "completion"] = "completion",
) -> CompletionProvider: ...
# Unbekannter component-Wert → ValueError (kein stiller Fallback auf den globalen Default)

def get_code_gen_provider(
    config: SddConfig,
) -> CodeGenProvider: ...
```

### 4.4 Konfigurationsauflösung (Hierarchie)

Die Factory löst die Konfiguration in drei Ebenen auf:

```
1. config.raw["llm"][component]         (z.B. "evaluator", "analyzer")
        ↓ fehlt?
2. config.raw["llm"]["completion"]      (globaler Completion-Default)
   bzw. config.raw["llm"]["code_gen"]   (globaler Code-Gen-Default)
        ↓ fehlt?
3. Built-in-Defaults (bestehende Anthropic/Claude-CLI-Konfiguration)
```

**Merge-Semantik: Feld-für-Feld, nicht Sektion-Ersatz.**
Felder werden von Ebene 1 → 2 → 3 ausgefüllt. Ist ein Feld in Ebene 1 gesetzt,
überschreibt es das gleichnamige Feld aus Ebene 2 — auch wenn Ebene 1 andere
Felder weglässt:

```yaml
# config.yaml:
llm:
  completion:
    provider: anthropic
    model: claude-haiku-4-5-20251001
  evaluator:
    provider: openai-compat   # nur provider, kein model, kein base_url
```
```
→ Merge-Ergebnis für evaluator:
    provider:  openai-compat          (aus llm.evaluator)
    model:     claude-haiku-4-5-20251001  (geerbt aus llm.completion)
    base_url:  FEHLT
    → ValueError: llm.evaluator.base_url fehlt (openai-compat erfordert base_url)
```

Felder eines anderen Komponenten-Overrides werden **nicht** geerbt (E-05):
`llm.analyzer.base_url` beeinflusst `llm.evaluator` nicht.

### 4.5 Einbindung in bestehende Komponenten

```python
# Evaluator
result = completion_provider.complete(prompt, timeout=timeout_per_scenario)
data = json.loads(result.text)           # JSON-Parsing beim Aufrufer

# Analyzer
result = completion_provider.complete(prompt)
return result.text                        # Analyzer parst JSON selbst

# AI-Routes
result = completion_provider.complete(prompt, system_prompt=SDD_SYSTEM_PROMPT, max_tokens=2048)
if result.usage:
    usage_store.record_usage(..., input_tokens=result.usage.input_tokens, ...)
return result.text

# Orchestrator
files, explanation = code_gen_provider.generate(prompt, workspace)
```

### 4.6 Provider-Lifecycle

Provider-Instanzen werden **einmalig pro Prozessstart** erzeugt — keine Factory-Aufrufe im
Request-Handler-Pfad oder pro Szenario-Schleife:

- **CLI-Kommandos** (`sdd evaluate`, `sdd orchestrate`): Factory-Aufruf am Anfang der
  Kommando-Funktion; Provider-Instanz als lokale Variable weitergereicht.
- **FastAPI** (`web/api/`): Provider-Instanzen als Modul-Variable oder via
  `app.state` bei `startup`; einmalig beim Start des Dev-Servers initialisiert.

Begründung: `openai.OpenAI()` und `anthropic.Anthropic()` bauen beim Konstruktoraufruf
einen HTTP-Connection-Pool auf — wiederholte Instanziierung pro Request erzeugt unnötigen
Overhead und kann zu Connection-Erschöpfung führen.

## 5. Konfigurationsschema

Die neue `llm`-Sektion in `.sdd/config.yaml` (ergänzt/ersetzt bestehende
`evaluator.model`-Felder, die deprecated werden):

```yaml
llm:
  # Globaler Default für alle CompletionProvider-Komponenten
  completion:
    provider: anthropic                  # anthropic | claude-cli | openai-compat
    model: claude-haiku-4-5-20251001
    # temperature: 0.0                  # Optional; Default 0.0; ignoriert bei claude-cli

  # Globaler Default für den CodeGenProvider (Orchestrator)
  code_gen:
    provider: claude-cli                 # claude-cli | openai-compat
    # model: ~                          # Pflicht für openai-compat
    # base_url: ~                       # Pflicht für openai-compat
    # api_key: ~                        # Optional; Default "lm-studio"; oder "${ENV_VAR}"

  # Optionale Komponenten-Overrides (erben nicht gesetzte Felder vom jeweiligen Default)
  # evaluator:                          # LLM-Provider für HOL-Planung + Bewertung
  #   provider: openai-compat           # Achtung: NICHT zu verwechseln mit
  #   base_url: "http://localhost:1234/v1"  # evaluator.base_url (HTTP-Endpunkt des
  #   model: "lmstudio-community/Meta-Llama-3.1-8B-Instruct-GGUF"  # Evaluator-Dienstes, SPEC-0003)
  #   # api_key: ~                      # Optional; oder "${ENV_VAR}"
  #   # temperature: 0.0               # Evaluator: deterministisch; Default passt
  #
  # analyzer:
  #   provider: openai-compat
  #   base_url: "http://localhost:1234/v1"
  #   model: "lmstudio-community/Meta-Llama-3.1-8B-Instruct-GGUF"
  #   # api_key: ~
  #
  # orchestrator:
  #   provider: openai-compat
  #   base_url: "http://localhost:1234/v1"
  #   model: "lmstudio-community/Meta-Llama-3.1-8B-Instruct-GGUF"
  #   # api_key: ~
  #
  # ai_routes:
  #   provider: openai-compat
  #   base_url: "http://localhost:1234/v1"
  #   model: "lmstudio-community/Meta-Llama-3.1-8B-Instruct-GGUF"
  #   temperature: 0.7                  # Empfohlen: kreativere Spec-Vorschläge
  #   # api_key: ~
```

### 5.1 Pflichtfelder je Provider

| Provider        | Pflicht             | Optional                          | Default `api_key`       | Default `temperature` |
|-----------------|---------------------|-----------------------------------|-------------------------|-----------------------|
| `anthropic`     | `model`             | `api_key`, `temperature`          | `ANTHROPIC_API_KEY` env | `0.0`                 |
| `claude-cli`    | –                   | –                                 | –                       | ignoriert             |
| `openai-compat` | `base_url`, `model` | `api_key`, `temperature`          | `"lm-studio"`           | `0.0`                 |

**`anthropic` ist kein gültiger Wert für `code_gen.provider` oder `orchestrator.provider`.**
`AnthropicCompletionProvider` implementiert ausschließlich `CompletionProvider`, nicht
`CodeGenProvider`. Die Factory wirft `ValueError` wenn `anthropic` als `code_gen`-Provider
konfiguriert wird. Gültige Werte für `code_gen`/`orchestrator`: `claude-cli | openai-compat`.

### 5.2 Backwards-Kompatibilität

| Altes Feld (deprecated)         | Auflösung durch Factory                   |
|---------------------------------|-------------------------------------------|
| `evaluator.model`               | → `llm.evaluator.model` → `llm.completion.model` |
| `evaluator.llm.*` (SPEC-0008 v0.2) | → `llm.evaluator.*`                   |

Fehlt die gesamte `llm`-Sektion, verhalten sich alle Komponenten identisch zu
v0.1.x (Anthropic SDK + Claude CLI, bisherige Hardcode-Defaults).

## 6. User Stories

| ID    | Als ...           | möchte ich ...                                               | um ...                                             |
|-------|-------------------|--------------------------------------------------------------|----------------------------------------------------|
| US-01 | Entwickler        | LM Studio für alle KI-Komponenten konfigurieren              | vollständig offline und privacy-konform zu arbeiten |
| US-02 | Entwickler        | bestehende Anthropic-Konfiguration unverändert nutzen        | keinen Migration-Aufwand zu haben                  |
| US-03 | DevOps-Engineer   | das LLM-Backend per config.yaml komponentenweise steuern     | z.B. Evaluator lokal, AI-Routes in der Cloud       |
| US-04 | Test-Entwickler   | Provider-Implementierungen gegen ein Mock austauschen        | Unit-Tests ohne echte API-Verbindung zu schreiben  |
| US-05 | Entwickler        | einen neuen Provider (z.B. Ollama) hinzufügen                | ohne bestehende Dateien zu ändern (OCP)            |

## 7. Funktionale Anforderungen

### Abstraktionsschicht

- **FR-01:** `tool/sdd_cli/llm/` wird als neues Sub-Package angelegt mit `base.py`, `factory.py` und `providers/`.
- **FR-02:** `CompletionProvider` und `CodeGenProvider` sind `typing.Protocol`-Klassen mit `@runtime_checkable`.
- **FR-03:** `get_completion_provider(config, component)` löst Provider und Konfiguration in der in §4.4 definierten Hierarchie auf.
- **FR-04:** `get_code_gen_provider(config)` löst Provider und Konfiguration aus `llm.orchestrator` → `llm.code_gen` → Claude-CLI-Default auf.

### Provider-Implementierungen

- **FR-05:** `AnthropicCompletionProvider`: lazy import `anthropic`; kein Modul-Level-Import.
- **FR-06:** `ClaudeCliCompletionProvider`: ruft `claude --print --output-format json -p <prompt>` auf; strippt den äußeren JSON-Envelope (`{"type":"result","result":"...","total_cost_usd":...}`); gibt `CompletionResult(text=<innerer result-Text>, usage=None)` zurück. `max_tokens` ignoriert; `system_prompt` als Präfix `<system>\n{system_prompt}\n</system>\n\n` eingefügt.
- **FR-07:** `OpenAICompatCompletionProvider`: lazy import `openai`; nutzt `client.chat.completions.create(model=..., messages=[...], max_tokens=..., temperature=temperature, timeout=timeout)`; gibt `CompletionResult(text=response.choices[0].message.content, usage=UsageMetadata(input_tokens=response.usage.prompt_tokens, output_tokens=response.usage.completion_tokens))` zurück. `temperature` aus Config (Default `0.0`).
- **FR-08:** `ClaudeCliCodeGenProvider`: bestehende `_call_code_gen_agent()`-Logik, in die neue Klasse extrahiert.
- **FR-09:** `OpenAICompatCodeGenProvider`: sendet Prompt mit JSON-Schema-Erwartung `{"files":[{"path":"...","content":"..."}],"explanation":"..."}` und schreibt Dateien selbst in `workspace`. **Path-Validierung (Pflicht):** Jeder `path`-Wert aus der LLM-Antwort muss nach `Path(workspace / path).resolve()` innerhalb von `workspace.resolve()` liegen — kein `..`-Traversal und kein absoluter Pfad außerhalb des Workspace. Ungültige Pfade → `ValueError`; der Orchestrator behandelt das als Code-Gen-Fehler und löst Retry aus (E-08). **Überschreib-Verhalten:** Existierende Dateien im Workspace werden ohne Rückfrage überschrieben — konsistent mit dem Verhalten des CLI-Agenten. Kein Backup, kein Fehler bei bereits vorhandenen Pfaden. Dies gilt auch bei Retry-Versuchen (zweiter Durchlauf überschreibt Ergebnis des ersten).

### Fehlerbehandlung

- **FR-10:** Fehlt `anthropic` bei `provider: anthropic` → `RuntimeError("pip install 'sdd-cli[evaluate]'")`.
- **FR-11:** Fehlt `openai` bei `provider: openai-compat` → `RuntimeError("pip install 'sdd-cli[lm-studio]'")`.
- **FR-12:** Fehlt `claude` CLI bei `provider: claude-cli` → `RuntimeError("claude CLI nicht gefunden")`.
- **FR-13:** Unbekannter `provider`-Wert → `ValueError` mit Liste erlaubter Werte.
- **FR-14:** Fehlendes Pflichtfeld (`base_url`, `model`) bei `openai-compat` → `ValueError` zum Zeitpunkt der Factory-Auflösung, nicht beim Laden der Config.

### Migration

- **FR-15:** `pyproject.toml` erhält neue optionale Dependency-Gruppe: `lm-studio = ["openai>=1.0", "httpx>=0.27"]`.
- **FR-16:** Alle bestehenden direkten LLM-Aufrufe in `evaluator.py`, `orchestrator.py`, `analyzer.py` und `routes/ai.py` werden durch Factory-Aufrufe ersetzt.

### Refaktor-Regressionsschutz

- **FR-17:** Vor jeder Ersetzung gemäß FR-16 **müssen Charakterisierungstests** für das
  bestehende Verhalten der betroffenen Funktion existieren und grün sein. Diese Tests
  bilden die "goldene Linie": sie müssen nach dem Refactor weiterhin grün sein.
  Schlägt ein Charakterisierungstest nach dem Refactor fehl, ist das ein Regressionsblock —
  kein optionaler Hinweis.

  **Gilt als allgemeines Projektmuster:** Jeder zukünftige Spec, der bestehende
  funktionierende Code ersetzt oder umbaut (Refactor-Specs), muss einen
  "Regressionsschutz"-Abschnitt in §12 enthalten, der die Charakterisierungstests
  der ersetzten Stellen benennt. Ohne diese Tests darf kein Merge erfolgen.

## 8. Nicht-funktionale Anforderungen

| Kategorie       | Anforderung                                                                               |
|-----------------|-------------------------------------------------------------------------------------------|
| Performance     | `timeout_per_scenario` (Evaluator) gilt für Provider-Aufrufe: der Evaluator übergibt den Wert als `timeout`-Parameter an `complete()`. `OpenAICompatCompletionProvider` und `AnthropicCompletionProvider` reichen ihn an den SDK-Request weiter; `ClaudeCliCompletionProvider` an `subprocess.run(timeout=...)`. |
| Security        | `api_key`-Werte erscheinen nie in Logs, Rich-Output, Report-JSON oder Subprocess-Argumenten. Enthält `config.yaml` einen echten Schlüsselwert, muss die Datei in `.gitignore` aufgenommen werden. Alternativ kann `api_key` als Env-Var-Referenz `${ENV_VAR_NAME}` angegeben werden; die Factory löst den Wert via `os.environ` auf und wirft `RuntimeError` wenn die Variable fehlt. |
| Testbarkeit     | Jede Provider-Klasse ist ohne Netzwerkverbindung testbar (alle externen Aufrufe mockbar)  |
| Backwards-Compat| Fehlt `llm`-Sektion → identisches Verhalten wie v0.1.x (kein Breaking Change)            |
| Erweiterbarkeit | Neuer Provider = neue Klasse in `providers/` + Eintrag in `factory.py` (OCP)             |
| Lazy Imports    | Kein `anthropic`- oder `openai`-Import auf Modul-Ebene; ausschließlich lazy imports       |

## 9. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: Pluggable LLM-Provider für alle KI-Komponenten

  Scenario: Evaluator nutzt LM Studio via openai-compat
    Given llm.evaluator.provider ist openai-compat in config.yaml
    And llm.evaluator.base_url und .model sind konfiguriert
    And ANTHROPIC_API_KEY ist nicht gesetzt
    When run_evaluation() ausgeführt wird
    Then werden LLM-Anfragen an die openai-compat base_url gesendet
    And kein Fehler wegen fehlendem ANTHROPIC_API_KEY wird geworfen

  Scenario: Orchestrator nutzt LM Studio via openai-compat
    Given llm.orchestrator.provider ist openai-compat in config.yaml
    And llm.orchestrator.base_url und .model sind konfiguriert
    When run_pipeline() ausgeführt wird
    Then wird der OpenAICompatCodeGenProvider genutzt
    And Dateien werden aus der JSON-Antwort in den Workspace geschrieben

  Scenario: Analyzer nutzt LM Studio via openai-compat
    Given llm.analyzer.provider ist openai-compat in config.yaml
    When analyze() aufgerufen wird
    Then wird openai.OpenAI gegen llm.analyzer.base_url verwendet
    And die JSON-Antwort wird korrekt geparst

  Scenario: Alle Defaults bleiben bei fehlender llm-Sektion erhalten
    Given die config.yaml enthält keine llm-Sektion
    When get_completion_provider(config, "evaluator") aufgerufen wird
    Then wird AnthropicCompletionProvider zurückgegeben

  Scenario: Dritter Provider hinzufügen ohne bestehende Dateien zu ändern
    Given eine neue Klasse OllamaCompletionProvider in providers/ollama.py
    And ein Eintrag "ollama" in factory.py
    And llm.evaluator.provider ist ollama in config.yaml
    When get_completion_provider(config, "evaluator") aufgerufen wird
    Then wird OllamaCompletionProvider zurückgegeben
    And evaluator.py, analyzer.py, orchestrator.py, ai.py wurden nicht verändert

  Scenario: Fehlende openai-Dependency bei openai-compat
    Given llm.completion.provider ist openai-compat
    And das openai-Paket ist nicht installiert
    When get_completion_provider(config) aufgerufen wird
    Then wird RuntimeError mit "pip install 'sdd-cli[lm-studio]'" geworfen

  Scenario: Komponenten-Override erbt model vom globalen Default
    Given llm.completion.provider ist anthropic
    And llm.completion.model ist "claude-haiku-4-5-20251001"
    And llm.evaluator.provider ist openai-compat
    And llm.evaluator enthält kein model-Feld
    And llm.evaluator.base_url ist "http://localhost:1234/v1"
    When get_completion_provider(config, "evaluator") aufgerufen wird
    Then wird OpenAICompatCompletionProvider mit model "claude-haiku-4-5-20251001" zurückgegeben

  Scenario: Komponenten-Override ohne base_url wirft ValueError
    Given llm.completion.provider ist anthropic
    And llm.evaluator.provider ist openai-compat
    And llm.evaluator enthält kein base_url-Feld
    And llm.completion enthält ebenfalls kein base_url-Feld
    When get_completion_provider(config, "evaluator") aufgerufen wird
    Then wird ValueError mit Hinweis auf fehlendes llm.evaluator.base_url geworfen
```

## 10. Edge Cases & Fehlerfälle

- **E-01:** `provider: openai-compat` ohne `base_url` → `ValueError` in Factory, nicht in `load_config()`.
- **E-02:** `provider: openai-compat` ohne `model` (bei Orchestrator) → `ValueError` in Factory.
- **E-03:** LM Studio nicht erreichbar → Provider wirft Exception; bestehende `_run_scenario_once()`-Fehlerbehandlung fängt ab.
- **E-04:** `OpenAICompatCodeGenProvider` erhält ungültiges JSON vom Modell → `json.JSONDecodeError` → Orchestrator behandelt als Code-Gen-Fehler, löst Retry aus.
- **E-05:** Komponenten-Override erbt fehlende Felder vom globalen Default, nicht von einem anderen Komponenten-Override.
- **E-06:** `claude-cli` als `code_gen.provider` + `claude` nicht im PATH → `RuntimeError` in `ClaudeCliCodeGenProvider.generate()`.
- **E-07:** `evaluator.model` (deprecated) und `llm.evaluator.model` beide gesetzt → `llm.evaluator.model` gewinnt (Factory-Hierarchie).
- **E-08:** `OpenAICompatCodeGenProvider` erhält `path`-Wert außerhalb von `workspace` (z.B. `../../.env`) → `ValueError` → Orchestrator behandelt als Code-Gen-Fehler, löst Retry aus.
- **E-09:** `api_key: "${MY_KEY}"` in `config.yaml` und `MY_KEY` nicht in `os.environ` → `RuntimeError` in der Factory beim Provider-Aufbau (nicht beim Config-Laden).

## 11. Contracts (was wird garantiert)

| Contract-ID | Typ      | Was wird garantiert?                                      |
|-------------|----------|-----------------------------------------------------------|
| CON-0022    | behavior | `CompletionProvider`-Interface und alle Implementierungen |
| CON-0023    | data     | Schema der neuen `llm`-Konfigurationssektion              |
| CON-0024    | behavior | `CodeGenProvider`-Interface und alle Implementierungen    |

## 12. Tests (wie wird verifiziert)

**Neue Provider-Tests:**

| Test-ID  | Level | Was prüft der Test?                                                           |
|----------|-------|-------------------------------------------------------------------------------|
| TST-0028 | unit  | Factory-Auflösung für `CompletionProvider` und `CodeGenProvider`; Merge-Hierarchie (E-05); `temperature`-Übergabe an Provider-Konstruktor |
| TST-0029 | unit  | `OpenAICompatCompletionProvider.complete()` — Request korrekt (Mock); `CompletionResult.usage` befüllt aus `response.usage` |
| TST-0030 | unit  | `OpenAICompatCodeGenProvider.generate()` — JSON→Dateien (Mock); Überschreib-Verhalten; Path-Traversal → `ValueError` (E-08) |
| TST-0031 | unit  | `ClaudeCliCompletionProvider.complete()` — Envelope gestrippt; `system_prompt`-Präfix korrekt; `timeout` an `subprocess.run`; `usage=None` |
| TST-0032 | unit  | `AnthropicCompletionProvider.complete()` — `system_prompt != None` → `cache_control: ephemeral`; `CompletionResult.usage` befüllt; `timeout` weitergegeben |

**Charakterisierungstests (Regressionsschutz gemäß FR-17):**

Diese Tests müssen **vor** dem jeweiligen FR-16-Refactor grün sein und **danach grün bleiben**.
Sie sichern das bestehende Verhalten der zu ersetzenden Call-Sites:

| Test-ID  | Level | Zu ersetzende Funktion             | Was wird gesichert                                                   |
|----------|----|---------------------------------------|----------------------------------------------------------------------|
| TST-0033 | unit | `evaluator._call_llm()`             | Eingabe: String-Prompt → Ausgabe: geparste `dict` mit Plan/Bewertungs-Schlüsseln; wirft bei fehlender `anthropic`-Dependency |
| TST-0034 | unit | `orchestrator._call_code_gen_agent()`| Eingabe: Prompt + workspace-Path → Ausgabe: `(list[dict], str)`; Dateiliste via git-diff; Timeout-Parameter wird an subprocess weitergereicht |
| TST-0035 | unit | `analyzer._call_claude()`           | Eingabe: String-Prompt → Ausgabe: roher Text (JSON-String); CLI-Envelope wird gestrippt |
| TST-0036 | unit | `ai._call()`                        | Eingabe: operation + user_message → Ausgabe: Text-String; `usage_store.record_usage()` wird aufgerufen mit korrekten Token-Counts |

Alle vier Charakterisierungstests mocken den externen Aufruf (SDK / subprocess) und prüfen
Input→Output-Vertrag, nicht die Netzwerkkommunikation.

## 13. Offene Fragen

- [x] Soll `ClaudeCliCompletionProvider` als valider Completion-Provider für Evaluator/Analyzer explizit unterstützt werden?
      → **Ja — `ClaudeCliCompletionProvider` implementiert `CompletionProvider` und ist für alle vier Komponenten nutzbar; `max_tokens` wird ignoriert, `system_prompt` als Prompt-Präfix eingefügt (FR-06)**
- [x] System-Prompt-Verlust bei AI-Routes nach Refactor?
      → **Behoben durch optionalen `system_prompt`-Parameter in `complete()` (§4.1); `AnthropicCompletionProvider` nutzt `cache_control: ephemeral`, kein Regression**
- [x] File-Discovery-Inkonsistenz zwischen CLI- und OpenAI-compat-Code-Gen-Provider?
      → **Interface-Invariante definiert: beide Provider liefern dieselbe `(files, explanation)`-Struktur; Ermittlungsmechanismus ist implementierungsspezifisch (§4.2)**
- [x] `anthropic` als gültiger `code_gen`-Provider?
      → **Explizit ausgeschlossen; Factory wirft `ValueError` (§5.1)**
- [x] `on_proc`-Verhalten bei nicht-CLI-Providern?
      → **Ignoriert, wird nie aufgerufen; im Interface-Vertrag dokumentiert (§4.2)**
- [x] `api_key`-Plaintext-Sicherheit?
      → **`.gitignore`-Empfehlung + Env-Var-Referenz `${ENV_VAR_NAME}` als Alternative (§8 NFR, E-09)**
- [x] `temperature=0` für alle Komponenten oder konfigurierbar?
      → **Konfigurierbar als optionales `temperature`-Feld pro Komponente; Default `0.0`; bei `claude-cli` ignoriert; empfohlener Override für `ai_routes: 0.7` (§4.1, §5, §5.1)**
- [x] Wie wird `timeout_per_scenario` an den Provider übergeben?
      → **Als `timeout`-Parameter in `complete()`; Evaluator belegt ihn, andere Komponenten lassen `None` (§4.1, §8)**
- [x] Überschreib-Verhalten bei `OpenAICompatCodeGenProvider` für existierende Dateien?
      → **Immer überschreiben, kein Backup — konsistent mit CLI-Agent-Verhalten; gilt auch bei Retries (FR-09)**
- [x] Token-Usage-Tracking geht nach Refactor verloren?
      → **`CompletionResult`-Rückgabetyp mit optionalem `UsageMetadata`-Feld; `ai.py` liest `result.usage` wenn nicht None (§4.1, §4.5, FR-06, FR-07)**
- [x] Provider-Lifecycle unspezifiziert?
      → **Einmalig pro Prozessstart; für FastAPI via `app.state`; keine Factory-Aufrufe im Request-Pfad (§4.6)**
- [x] Namenskonflikt `evaluator.base_url` vs. `llm.evaluator.base_url`?
      → **Erklärender Kommentar im Config-Schema (§5)**
- [ ] Wie verhält sich `cost_alert_usd` bei `openai-compat` ohne Token-Preisangaben? Deaktivieren oder auf `inf` setzen?
      _(Nicht-blockierend: `cost_alert_usd` ist im aktuellen Code noch nicht implementiert)_
- [ ] Soll die Factory beim Start von `sdd evaluate`/`sdd orchestrate` den aktiven Provider ausgeben (Observability)?
- [ ] Welches Modell wird für `OpenAICompatCodeGenProvider` empfohlen? Code-Gen erfordert stärkere Modelle als Evaluation.

## 14. Änderungshistorie

| Datum      | Version | Autor   | Änderung                                                                              |
|------------|---------|---------|---------------------------------------------------------------------------------------|
| 2026-05-12 | 0.1.0   | Boris   | Initiale Erstellung (Template)                                                        |
| 2026-05-13 | 0.2.0   | Boris   | Evaluator-spezifisch ausgearbeitet (nur `evaluator.llm`)                              |
| 2026-05-13 | 0.3.0   | Boris   | Vollständige Überarbeitung: SOLID-Provider-Pattern für alle 4 Komponenten; zwei Interfaces; Factory; einheitliches `llm`-Config-Schema |
| 2026-05-13 | 0.4.0   | Boris   | Review-Findings eingearbeitet: `system_prompt`-Parameter in `CompletionProvider.complete()` (System-Prompt-Verlust AI-Routes), `max_tokens`-Verhalten je Provider, File-Discovery-Invariante in CodeGenProvider-Kontrakt, `on_proc`-Vertrag für nicht-CLI-Provider, `component: Literal[...]`, Merge-Semantik §4.4 mit Beispiel, `anthropic`-Ausschluss für code_gen §5.1, Path-Validierung FR-09+E-08, api_key-Security §8+E-09, zwei neue Gherkin-Szenarien §9, §13 abgehakt |
| 2026-05-13 | 0.5.0   | Boris   | Zweiter Review eingearbeitet: `timeout`-Parameter in `complete()` (§4.1, §8), `temperature` als Config-Feld pro Komponente (§4.1, §5, §5.1, FR-07), Überschreib-Verhalten FR-09, TST-0031 für `ClaudeCliCompletionProvider`, TST-0028–0030 erweitert, §13 abgehakt |
| 2026-05-13 | 0.6.0   | Boris   | Dritter Review + Regressionsschutz: `CompletionResult`/`UsageMetadata`-Rückgabetyp (§4.1, FR-06/07), Token-Usage-Erhalt in `ai.py` (§4.5), Provider-Lifecycle §4.6, Namenskonflikt §5 kommentiert, Gherkin-Szenario OCP mit `When` (§9), TST-0032 `AnthropicCompletionProvider`, Charakterisierungstests TST-0033–0036 + FR-17 Regressionsschutz-Pflicht als Projektmuster, §13 abgehakt |
