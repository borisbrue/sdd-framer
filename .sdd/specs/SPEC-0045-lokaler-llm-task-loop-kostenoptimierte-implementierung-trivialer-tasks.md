---
id: SPEC-0045
title: Lokaler LLM Task-Loop – Kostenoptimierte Implementierung trivialer Tasks
type: feature
status: implemented
owner: Boris
created: 2026-06-10
updated: '2026-06-10'
version: 0.2.0
priority: high
tags:
- llm
- tasks
- cost-optimization
- tdd
- local-llm
depends_on:
- SPEC-0008
- SPEC-0011
- SPEC-0016
- SPEC-0026
- SPEC-0035
- SPEC-0036
- SPEC-0037
contracts:
- CON-0171
- CON-0172
- CON-0173
- CON-0174
tests:
- TST-0197
- TST-0198
- TST-0199
- TST-0200
fr_test_map:
  FR-01:
  - TST-0197
  - TST-0200
  FR-02:
  - TST-0197
  FR-03:
  - TST-0198
  FR-04:
  - TST-0199
  FR-05:
  - TST-0199
  FR-06:
  - TST-0199
  FR-07:
  - TST-0199
  FR-08:
  - TST-0200
adrs: []
started_at: '2026-06-10T13:17:34Z'
---
# Lokaler LLM Task-Loop – Kostenoptimierte Implementierung trivialer Tasks

> **Status:** approved · **Owner:** Boris · **Version:** 0.2.0

## 1. Kontext & Motivation

In der aktuellen `sdd-implement`-Pipeline übernimmt Claude alle Tasks — unabhängig
davon, ob sie trivial oder komplex sind. Das erzeugt unnötige Kosten: einfache
Ein-File-Änderungen oder klar abgegrenzte Funktionen benötigen keine
frontier-LLM-Kapazität für die Implementierung selbst, sondern lediglich für den Review.

Ziel ist ein hybrider Ausführungspfad: Einfache Tasks werden an ein lokales LLM
(z.B. Ollama) delegiert, das im TDD-Zyklus arbeitet — Test schreiben, dagegen
implementieren. Claude übernimmt ausschließlich die Überprüfung des Ergebnisses
und bei Bedarf die Kontext-Anreicherung für Retries oder die Eskalation.

## 2. Zielsetzung

**Primärziel:**
Den Anteil der Tasks, die ohne Claude-Implementierungstoken abgeschlossen werden,
maximieren — ohne Qualitätsverlust durch Claude-Review als Gate.

**Erfolgskriterien (messbar):**
- [ ] X% der Tasks werden vollständig vom lokalen LLM implementiert und von Claude
      als korrekt bestätigt (Baseline nach erster Produktionsmessung festlegen)
- [ ] Jeder Task, der das lokale LLM durchläuft, hat einen vom LLM geschriebenen
      Test, der vor der Implementierung existierte
- [ ] Kein Task wird als abgeschlossen markiert, ohne Claude-Review zu passieren
- [ ] Konfigurierbare Schwelle für Komplexitäts-Routing ist dokumentiert und testbar

**Nicht-Ziele (explizit):**
- Kein automatisches Deployment nach erfolgreichem Task-Loop
- Keine Änderungen am Spec- oder Contract-Format
- Kein Support für Cloud-LLMs außer Claude als Reviewer
- Keine Änderung an der Decompose-Ausgabe (nur Anreicherung um Komplexitäts-Score)

## 3. User Stories

| ID    | Als …              | möchte ich …                                                              | um …                                              |
|-------|--------------------|---------------------------------------------------------------------------|---------------------------------------------------|
| US-01 | sdd-implement      | triviale Tasks automatisch an ein lokales LLM delegieren                  | Claude-Token nur für Review und Komplexes zu nutzen |
| US-02 | Entwickler         | in der Task-Ausgabe sehen, welches LLM einen Task bearbeitet hat          | Transparenz über den Ausführungspfad zu haben      |
| US-03 | Entwickler         | den Routing-Schwellenwert konfigurieren                                   | das Verhalten an Projektgröße anzupassen           |
| US-04 | sdd-implement      | bei einem fehlgeschlagenen lokalen LLM-Versuch Kontext anreichern         | die Retry-Chance zu verbessern                     |
| US-05 | Entwickler         | nach N Fehlversuchen automatisch zu Claude eskalieren                     | keinen Task in einem endlosen Retry-Loop zu verlieren |

## 4. Funktionale Anforderungen

- **FR-01 – Komplexitäts-Score im Decompose:**
  Jeder Task erhält nach der Decomposition einen `complexity_score` (integer, 0–100).
  Der Score basiert auf einer Heuristik: Anzahl der betroffenen Dateien, geschätzte
  Zeilen geänderter Code, Anzahl abhängiger Contracts. Sind historische Token-Daten
  aus SPEC-0011 (`sdd estimate`) für vergleichbare Tasks vorhanden, fließen sie als
  zusätzliches Feature in den Score ein. Ein konfigurierbarer Schwellenwert
  (`task_routing.complexity_threshold`, Default: 30) entscheidet über das Routing.

- **FR-02 – Routing-Entscheidung:**
  Tasks mit `complexity_score ≤ threshold` werden in die lokale LLM-Queue eingestellt.
  Tasks oberhalb des Schwellenwerts werden direkt von Claude übernommen (bestehender Pfad).
  Die Routing-Entscheidung wird im Task-Objekt als `executor: local | claude` gespeichert.
  Das Routing ist eine Ebene **über** dem LLM-Provider: `LocalLLMExecutor` delegiert intern
  an `get_completion_provider(config, "local_llm")` (SPEC-0008 Factory), `ClaudeExecutor`
  an `get_code_gen_provider(config)`. Es wird kein neues Provider-Interface eingeführt —
  `TaskExecutor` ist ein Orchestrierungs-Interface, kein Duplikat von `CompletionProvider`.

- **FR-03 – Lokaler TDD-Loop (async):**
  Das lokale LLM erhält einen strukturierten Prompt-Kontext bestehend aus:
  Task-Beschreibung, betroffene Dateien (Inhalt), zugehöriger Contract (falls vorhanden).
  Pflichtablauf (nicht verhandelbar):
  1. Test schreiben (Datei `tests/unit/test_<task_id>.py`)
  2. Implementierung gegen den Test entwickeln
  3. Test-Ausführung via `pytest` — Ergebnis (pass/fail + Output) wird festgehalten
  Der Loop läuft als `asyncio`-Coroutine. Mehrere unabhängige Tasks können gleichzeitig
  ausgeführt werden (bis zu `task_routing.max_concurrent`, Default: 3). pytest-Aufrufe
  laufen via `asyncio.create_subprocess_exec` um den Event-Loop nicht zu blockieren.

- **FR-04 – Ergebnis-Rückgabe an Claude mit Prompt Caching:**
  Nach Abschluss des lokalen TDD-Loops übergibt das System an Claude den vollen Kontext,
  aufgeteilt in zwei Teile:
  - **Gecachtes Prefix** (`cache_control: {"type": "ephemeral"}`): Spec-Inhalt + Contract-Inhalt.
    Wird einmalig pro `sdd-implement`-Lauf gesetzt; nachfolgende Tasks nutzen denselben
    Cache (5-Minuten-Fenster, synchroner Loop hält es warm).
  - **Nicht-gecachter Teil** (pro Task): Diff der Änderungen, Test-Code, `pytest`-Ausgabe,
    Anzahl der Iterationen, Retry-Kontext (falls vorhanden).
  Claude prüft ausschließlich: "Ist das Ergebnis funktional korrekt und contract-konform?"

- **FR-05 – Review-Gate durch Claude:**
  Claude bewertet das Ergebnis binär (pass / fail mit Begründung).
  Bei `pass`: Task-Status → `completed`, `executor: local` bleibt erhalten.
  Bei `fail`: Begründung wird als Kontext-Anreicherung für den nächsten Retry übergeben.

- **FR-06 – Retry-Loop mit Kontext-Anreicherung:**
  Bei `fail` startet das lokale LLM einen neuen Versuch mit dem ursprünglichen Kontext
  plus Claudes Fehlerbegründung (akkumulativ über Iterationen). Maximale Retry-Anzahl
  ist konfigurierbar (`task_routing.max_retries`, Default: 3).
  **Abgrenzung zu SPEC-0004:** Der Retry-Loop hier bezieht sich auf Code-Generierungsversuche
  (kann das lokale LLM den Task implementieren?), nicht auf Holdout-Szenario-Bewertungen.
  Die Evaluator-Infrastruktur aus SPEC-0004 (3× mit 2/3-Pass-Threshold) ist eine separate
  Qualitätsprüfung und kein Kandidat zur Wiederverwendung hier.

- **FR-07 – Eskalation zu Claude:**
  Nach Erreichen von `max_retries` ohne `pass` übernimmt Claude den Task vollständig
  (bestehender Implementierungspfad). Der Task wird als `executor: claude (escalated)`
  markiert und der akkumulierte Kontext aus den Retries mitgeliefert.

- **FR-08 – Konfiguration:**
  Die LLM-Anbindung wird als Komponenten-Override in die bestehende `llm`-Sektion
  aus SPEC-0008 integriert. Routing-Parameter erhalten einen eigenen `task_routing`-Block:
  ```yaml
  llm:
    local_llm:                              # Komponenten-Override (SPEC-0008 Factory)
      provider: openai-compat              # → OpenAICompatCompletionProvider
      base_url: "http://localhost:11434/v1" # Ollama / LM Studio / llama.cpp
      model: "qwen2.5-coder:14b"           # frei wechselbar, kein Pflichtmodell

  task_routing:                             # Routing-Parameter (unabhängig vom Provider)
    enabled: true
    complexity_threshold: 30
    max_retries: 3
    max_concurrent: 3                       # gleichzeitige async Tasks
  ```
  Kein separater `local_llm`-Top-Level-Block — die Anbindung nutzt `get_completion_provider(
  config, "local_llm")` und erbt alle SPEC-0008-Mechanismen (Fehlerbehandlung, Lazy Imports,
  api_key-Env-Var-Unterstützung). Backends werden über `OpenAICompatCompletionProvider`
  (SPEC-0008) angebunden; für HuggingFace-Modelle steht alternativ `provider: huggingface`
  (SPEC-0013) zur Verfügung. Ist `llm.local_llm` nicht konfiguriert, verhält sich
  `task_routing.enabled: true` wie `false` (kein lokaler Provider → alle Tasks zu Claude).

## 5. Architektur & Design Patterns

### Strategy Pattern
**Begründung:** Die Task-Ausführung ist eine austauschbare Strategie — `LocalLLMExecutor`
und `ClaudeExecutor` implementieren dasselbe Interface `TaskExecutor`. Das Routing wählt
zur Laufzeit die passende Strategie anhand des `complexity_score`. Neue Executors
(z.B. anderes lokales Modell) können ohne Änderung des Routing-Codes hinzugefügt werden.

**Abgrenzung zu SPEC-0008:** `TaskExecutor` operiert auf Task-Ebene (Routing + TDD-Loop +
Report). Es ist kein Duplikat von `CompletionProvider`/`CodeGenProvider`, sondern ein
Konsument dieser Interfaces. `LocalLLMExecutor` delegiert LLM-Calls intern an
`get_completion_provider(config, "local_llm")`, `ClaudeExecutor` an
`get_code_gen_provider(config)`. Es werden keine neuen Provider-Klassen eingeführt.
[Refactoring Guru – Strategy](https://refactoring.guru/design-patterns/strategy)

### Chain of Responsibility
**Begründung:** Der Retry-Loop bildet eine Kette von Verarbeitungsschritten:
`LocalLLMExecutor → ClaudeReviewer → (retry: LocalLLMExecutor+Context) → … → EscalationHandler`.
Jedes Glied entscheidet, ob es den Task abschließt oder an das nächste weiterreicht.
Das Muster hält die Eskalationslogik aus dem Executor-Code heraus.
[Refactoring Guru – Chain of Responsibility](https://refactoring.guru/design-patterns/chain-of-responsibility)

### Template Method
**Begründung:** Der TDD-Ablauf (test → implement → run → report) ist ein fixer Skelett-
Algorithmus. Einzelne Schritte (Prompt-Generierung, Test-Runner-Aufruf) können
überschrieben werden, ohne die Reihenfolge zu brechen.
[Refactoring Guru – Template Method](https://refactoring.guru/design-patterns/template-method)

## 6. Contracts (was wird garantiert)

*(werden nach Spec-Approval ergänzt)*

## 7. Tests (wie wird verifiziert)

*(werden nach Contract-Approval ergänzt)*

## 8. Offene Fragen

- [x] Wie wird `complexity_score` initial kalibriert? Gibt es historische Task-Daten
      aus SPEC-0035 (Token-Tracking), die als Baseline dienen können?
      → Keine historischen Daten vorhanden. Starten mit reiner Heuristik (FR-01).
- [x] Welches lokale Modell ist Pflicht-Referenz für die erste Implementierung?
      → Kein festes Pflichtmodell. Integration gegen OpenAI-compatible API
        (LM Studio / Ollama / llama.cpp). Modell ist vollständig über `local_llm.model`
        konfigurierbar und zur Laufzeit wechselbar.
- [x] Soll der lokale LLM-Loop synchron im `sdd-implement`-Prozess laufen oder
      als asynchrone Coroutine-basierte Ausführung?
      → **Async via `asyncio`.** Mehrere unabhängige Tasks laufen gleichzeitig (bis zu
        `task_routing.max_concurrent`). pytest-Aufrufe via `asyncio.create_subprocess_exec`.
        Im CLI-Kontext: `asyncio.run(execute_task_loop(...))`.
        **Abgrenzung zu SPEC-0016:** SPEC-0016's `asyncio.create_task()` + `JobStore` gilt
        für Web-UI-Kontext (Browser darf nicht blockieren). Der `sdd implement`-CLI-Befehl
        nutzt `asyncio` intern für parallele Task-Ausführung — kein separater HTTP-Job-Broker,
        kein Polling-Endpoint. Bei zukünftiger Web-UI-Integration von `sdd implement` wird
        SPEC-0016's `JobStore`-Infrastruktur wiederverwendet.
- [x] Soll Claude beim Review nur das Diff sehen oder den vollständigen Task-Kontext?
      → Voller Kontext. Spec + Contract werden als gecachtes Prompt-Prefix übertragen
        (`cache_control: {"type": "ephemeral"}`). Da der Loop synchron läuft, bleibt
        das 5-Minuten-Cache-Fenster über alle Tasks warm. Nur der task-spezifische
        Teil (Diff, Test-Code, pytest-Output) ist nicht gecacht.

## 9. Implementierungsreihenfolge

1. `complexity_score`-Heuristik in Decompose-Phase implementieren (FR-01)
2. `task_routing`-Konfigurationsblock in `config.yaml` + Loader ergänzen; `llm.local_llm`
   als Komponenten-Override in SPEC-0008-Factory registrieren (FR-08)
3. `TaskExecutor`-Interface + `LocalLLMExecutor`-Stub anlegen; intern
   `get_completion_provider(config, "local_llm")` nutzen (Strategy, SPEC-0008)
4. Async TDD-Loop im `LocalLLMExecutor` implementieren: Prompt → Test → Implement →
   `asyncio.create_subprocess_exec(pytest)` (FR-03)
5. Semaphore-basierte Concurrency-Steuerung (`max_concurrent`) + `asyncio.gather` für
   parallele Task-Ausführung
6. Routing-Logik in `sdd-implement` integrieren (FR-02)
7. Claude-Review-Gate implementieren (FR-04 + FR-05)
8. Retry-Loop mit Kontext-Anreicherung (FR-06)
9. Eskalations-Handler (FR-07)
10. Task-Output um `executor`-Feld erweitern (US-02)
11. Tests & Validierung

## 10. Änderungshistorie

| Datum      | Version | Autor  | Änderung            |
|------------|---------|--------|---------------------|
| 2026-06-10 | 0.1.0   | Boris  | Initiale Erstellung |
| 2026-06-10 | 0.2.0   | Boris  | Regression-Konflikte aufgelöst: TaskExecutor als Konsument von SPEC-0008-Providern (kein Duplikat); `task_routing`-Konfigblock statt `local_llm`-Top-Level; async TDD-Loop mit `max_concurrent`; SPEC-0011/0013/0016-Referenzen ergänzt; SPEC-0004-Abgrenzung für Retry-Loop |
