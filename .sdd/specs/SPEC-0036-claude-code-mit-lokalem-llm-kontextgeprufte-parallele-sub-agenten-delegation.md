---
id: SPEC-0036
title: Claude Code mit lokalem LLM – Kontextgeprüfte Parallele Sub-Agenten-Delegation
type: feature
status: deprecated
owner: borisbrue
created: 2026-06-05
updated: '2026-06-05'
version: 0.2.0
priority: high
tags:
- local-llm
- parallelization
- cost-reduction
- sub-agents
- ollama
- lm-studio
- llama-cpp
depends_on:
- SPEC-0008
- SPEC-0011
- SPEC-0026
- SPEC-0035
contracts:
- CON-0125
- CON-0126
- CON-0127
- CON-0128
- CON-0129
tests:
- TST-0147
- TST-0148
- TST-0149
- TST-0150
- TST-0151
adrs: []
started_at: '2026-06-05T09:40:56Z'
deprecated_reason: "Lokaler Agent und DagScheduler nie angebunden; abgelöst durch die Rollen-Pipeline"
replaced_by: "SPEC-0053"
---
# Claude Code mit lokalem LLM – Kontextgeprüfte Parallele Sub-Agenten-Delegation

> **Status:** draft · **Owner:** borisbrue · **Version:** 0.1.0

## 1. Kontext & Motivation

`sdd implement` delegiert heute Tasks sequenziell an Cloud-Claude (SPEC-0035).
Jeder Task kostet Anthropic-API-Token — auch für einfache, repetitive Aufgaben
(Boilerplate, Tests, Config-Dateien), die ein kleines lokales Modell problemlos
erledigen könnte.

Zwei Probleme:

1. **Kosten:** Alle Tasks laufen auf Cloud-Claude, unabhängig von ihrer
   Komplexität. Einfache Tasks könnten kostenfrei lokal laufen.
2. **Geschwindigkeit:** SPEC-0035 ist sequenziell. Unabhängige Tasks könnten
   parallel laufen — Cloud-Claude orchestriert, lokale Sub-Agenten führen aus.

Die Lösung: Claude Code CLI unterstützt `ANTHROPIC_BASE_URL` als Umgebungsvariable.
Zeigt diese URL auf einen Anthropic→OpenAI-kompatiblen Proxy (z.B. LiteLLM), läuft
Claude Code CLI transparent gegen ein lokales Modell (Ollama, LM Studio, llama.cpp).

Vor der Delegation prüft der Orchestrator, ob der Task-Kontext (Spec-Abschnitt +
Contracts + Test-Stubs + Code-Dateien) in das Context-Window des lokalen Modells
passt. Passt er — lokal. Passt er nicht — Cloud.

**Abgrenzung zu SPEC-0013 (HuggingFace-Integration):** SPEC-0013 nutzt lokale
HuggingFace-Transformer-Modelle direkt für *Completion*-Aufgaben (Analyse,
Bewertung) innerhalb des Python-Prozesses. SPEC-0036 nutzt lokale LLMs als
vollständige *Code-Generierungsagenten* via Claude Code CLI-Subprocess mit
Proxy-Adapter — unterschiedliche Anwendungsfälle ohne Überschneidung.

## 2. Zielsetzung

**Primärziel:**
Boris startet `sdd implement SPEC-XXXX`. Claude übernimmt Orchestrierung und
Kontext-Check; unabhängige Tasks laufen parallel auf lokalen Sub-Agenten (Ollama /
LM Studio / llama.cpp via Proxy), abhängige Tasks werden sequenziell dispatcht.
Cloud-API-Kosten sinken messbar.

**Erfolgskriterien (messbar):**
- [ ] `sdd implement SPEC-XXXX` zeigt pro Task: `[LOCAL: llama3.1:8b]` oder
      `[CLOUD: claude-sonnet-4-6]`
- [ ] Unabhängige Tasks werden parallel ausgeführt (max. `local_agent.max_parallel`,
      default 4)
- [ ] `sdd calibrate SPEC-XXXX` zeigt Kosten-Breakdown: Cloud-Token vs. lokale Token
- [ ] Kontext-Check schlägt fehl → Task läuft auf Cloud, kein Silent-Failure
- [ ] Proxy-URL, Modell, Context-Window und max_parallel sind in `.sdd/config.yaml`
      konfigurierbar ohne Code-Änderung
- [ ] Schlägt der lokale Sub-Agent fehl: 1 Retry lokal, dann Eskalation auf Cloud

**Nicht-Ziele (explizit):**
- Kein eigenes Proxy-Protokoll — LiteLLM oder kompatibler Anthropic→OpenAI-Adapter
  ist Voraussetzung und wird nicht selbst gebaut
- Keine qualitätsbasierte Modell-Auswahl (nur Kontext-Größe und Konfiguration
  entscheiden das Routing)
- Kein Fine-Tuning lokaler Modelle
- Kein Multi-User-Support
- Keine eigene LLM-Laufzeit (Ollama / LM Studio / llama.cpp als externe Dienste)
- Kein gleichzeitiger Cloud+Lokal-Betrieb für denselben Task
- Kein austauschbarer Tokenizer — tiktoken (cl100k_base) ist fest; kein `tokenize`-Endpoint von Ollama o.ä.

## 3. Architektur & Design Patterns

### Pattern 1 — Strategy
> [Refactoring Guru – Strategy](https://refactoring.guru/design-patterns/strategy)

`LlmRoutingStrategy` ist ein austauschbares Protocol. Die einzige aktuelle
Implementierung ist `ContextSizeRoutingStrategy`: Sie zählt Tokens im Task-Kontext
und vergleicht mit dem konfigurierten `context_window` des lokalen Modells.
Zukünftige Strategien (z.B. `CostRoutingStrategy`, `TagRoutingStrategy`) können
hinzugefügt werden ohne bestehenden Code zu ändern (OCP).

**Begründung:** Das Routing-Kriterium wird sich weiterentwickeln. Strategy isoliert
die Entscheidungslogik und macht sie einzeln testbar.

**Abgrenzung zu SPEC-0008 Provider-Factory:** Die Factory entscheidet *welche*
LLM-Implementierung genutzt wird (anthropic / openai-compat / claude-cli) innerhalb
eines laufenden Agenten-Kontexts. `LlmRoutingStrategy` entscheidet *wo* ein Task
ausgeführt wird (lokaler Subprocess vs. Cloud-Sub-Agent-Prozess). Beide Entscheidungen
sind orthogonal — die Factory läuft *nach* dem Routing, innerhalb des gewählten Proxys.

```python
class LlmRoutingStrategy(Protocol):
    def route(self, task: TaskContext) -> Literal["local", "cloud"]: ...

class ContextSizeRoutingStrategy:
    def route(self, task: TaskContext) -> Literal["local", "cloud"]:
        estimated = self._count_tokens(task)
        fits = estimated + self.reserve <= self.context_window
        return "local" if fits and self.enabled else "cloud"
```

### Pattern 2 — Proxy
> [Refactoring Guru – Proxy](https://refactoring.guru/design-patterns/proxy)

`LocalSubAgentProxy` implementiert dasselbe Interface wie der Cloud-Sub-Agent
(aus SPEC-0035), startet aber einen Claude Code CLI-Subprocess mit
`ANTHROPIC_BASE_URL` auf den konfigurierten Proxy gesetzt. Für den DAG-Scheduler
ist ein lokaler und ein Cloud-Sub-Agent nicht unterscheidbar.

**Begründung:** Der DAG-Scheduler muss nicht wissen ob ein Task lokal oder in der
Cloud läuft. Der Proxy kapselt die technische Differenz (Env-Override,
Proxy-Verbindung) vollständig.

**Abgrenzung zu SPEC-0008 LlmProvider-Protocol:** `LlmProvider` (SPEC-0008) operiert
auf Completion-Ebene *innerhalb* eines laufenden Agenten-Kontexts (ein Prompt → ein
Ergebnis). `SubAgentProxy` operiert auf Task-Ebene: er spawnt einen vollständigen
Claude Code CLI-Prozess, der seinerseits intern einen LlmProvider nutzt. Die beiden
Schichten sind komplementär, nicht konkurrierend.

```python
class SubAgentProxy(Protocol):
    def execute(self, task: TaskContext) -> SubAgentResult: ...

class LocalSubAgentProxy:
    def execute(self, task: TaskContext) -> SubAgentResult:
        env = os.environ.copy()
        env["ANTHROPIC_BASE_URL"] = self.proxy_url
        env["ANTHROPIC_API_KEY"] = self.api_key  # Proxy-seitiger Dummy-Key
        # subprocess: claude --print --dangerously-skip-permissions
        ...

class CloudSubAgentProxy:
    def execute(self, task: TaskContext) -> SubAgentResult:
        # Agent SDK (SPEC-0035)
        ...
```

### Pattern 3 — Observer
> [Refactoring Guru – Observer](https://refactoring.guru/design-patterns/observer)

Der `DagScheduler` ist Subscriber auf Task-Completion-Events. Sobald ein
Sub-Agent (lokal oder Cloud) einen Task abschließt, prüft der Scheduler welche
bisher blockierten Tasks nun alle Abhängigkeiten erfüllt haben und dispatcht sie
in den nächsten freien Slot (bis `max_parallel`).

**Begründung:** Vermeidet aktives Polling über Task-Status. Der Scheduler reagiert
ereignisgesteuert und hält die Parallelitätssteuerung sauber vom Ausführungskontext
getrennt.

**Abgrenzung zu SPEC-0016 Async-Background-Jobs:** SPEC-0016's Job-Infrastruktur
verwaltet HTTP-Request-Ebene Jobs (Spec-Analyse, Pipeline-Runs) über FastAPI mit
persistentem `AnalysisJobStore`. `DagScheduler` ist ein prozess-internes
Koordinationswerkzeug für `sdd implement`-Subprozesse — kein HTTP-Layer, kein
persistenter Store, keine Infrastruktur-Überschneidung.

### Datenfluss

```
sdd implement SPEC-XXXX
    │
    ├── sdd decompose SPEC-XXXX
    │       → TaskDag { tasks: [...], edges: [(A→B), ...] }
    │
    ├── Proxy-Health-Check (optional, per config)
    │
    └── DagScheduler.run(dag, max_parallel=4)
            │
            ├── Alle root-Tasks (keine Deps) → bereit
            │
            └── für jeden bereiten Task (bis max_parallel Slots frei):
                    │
                    ├── ContextSizeRoutingStrategy.route(task) → "local" | "cloud"
                    │       └── Tokens zählen: task_desc + spec_section + contracts
                    │           + test_stubs + code_files
                    │           vs. context_window - context_reserve_tokens
                    │
                    ├── SubAgentProxy auswählen (Local | Cloud)
                    │
                    ├── [Decorator: Token-Context öffnen] (SPEC-0035)
                    ├── proxy.execute(task)  →  SubAgentResult + usage
                    ├── [Decorator: Token persistieren]  (SPEC-0035)
                    │
                    ├── bei Fehler: 1 Retry auf demselben Proxy
                    │   bei erneutem Fehler (lokal): CloudSubAgentProxy.execute(task)
                    │   bei erneutem Fehler (cloud): Orchestrator hält an
                    │
                    └── Task-Completion-Event → Observer → nächste bereite Tasks
```

## 4. Funktionale Anforderungen

- **FR-01:** `sdd decompose SPEC-XXXX` gibt einen Task-DAG aus mit expliziten
  Abhängigkeitskanten (`depends_on: [task_id, ...]`) pro Task.
  _(Erweiterung des bestehenden Decompose-Outputs aus SPEC-0026/SPEC-0035)_

- **FR-02:** `ContextSizeRoutingStrategy` zählt Tokens im Task-Kontext:
  Task-Beschreibung + relevante Spec-Abschnitte + referenzierte Contracts +
  Test-Stubs + Code-Dateien aus dem Decompose-Output (explizite Dateiliste pro Task,
  nicht heuristisch ermittelt). Token-Zählung via `tiktoken` (cl100k_base).
  Um Duplizierung mit SPEC-0011 zu vermeiden, wird die Zähl-Logik als gemeinsame
  `ContextTokenCounter`-Utility in `tool/sdd_cli/estimation.py` (SPEC-0011-Modul)
  extrahiert und von SPEC-0036 importiert — keine zweite tiktoken-Implementierung.

- **FR-03:** Task wird als `"local"` geroutet wenn:
  `estimated_tokens + context_reserve_tokens ≤ local_agent.context_window`
  AND `local_agent.enabled = true`.
  Sonst `"cloud"`. Kein Silent-Routing.

- **FR-04:** `LocalSubAgentProxy.execute()` startet Claude Code CLI als Subprocess
  mit `ANTHROPIC_BASE_URL` und `ANTHROPIC_API_KEY` aus der Konfiguration gesetzt.
  Der Proxy-Key ist ein beliebiger String (wird vom lokalen Proxy nicht validiert).

- **FR-05:** `DagScheduler` dispatcht Tasks ereignisgesteuert: sobald alle
  Abhängigkeiten eines Tasks `completed` sind, wird er in den nächsten freien Slot
  eingereiht. Lokale und Cloud-Slots werden getrennt gezählt:
  max. `local_agent.max_parallel_local` parallele lokale Sub-Agenten und
  max. `local_agent.max_parallel_cloud` parallele Cloud-Sub-Agenten.

- **FR-06:** Der Output zeigt pro Task-Start eine Zeile:
  `[LOCAL: llama3.1:8b] Task-3: Implement UserRepository`
  `[CLOUD: claude-sonnet-4-6] Task-4: Implement AuthMiddleware (context too large)`

- **FR-07:** Token-Verbrauch wird pro Task in `token-history` gespeichert mit
  `agent_type: "local" | "cloud"` und `model`-Feld. Diese Schema-Erweiterung
  erfolgt **koordiniert mit SPEC-0011**: `agent_type` und `model` werden als
  optionale Felder in das bestehende Schema (`evaluations.db`, SPEC-0011 §6)
  integriert — keine separate Migration, kein zweites Schema. Die Änderung wird
  in SPEC-0011 als Erweiterungsreferenz eingetragen.

- **FR-08:** Erweiterung des bestehenden `sdd calibrate`-Commands aus SPEC-0011
  (nicht neu definiert): der Output wird um `cloud_tokens` / `local_tokens`-Zeilen
  ergänzt. Format und Command-Name bleiben identisch zu SPEC-0011; die Erweiterung
  wird in SPEC-0011 als Abhängigkeit referenziert.

- **FR-09:** Schlägt ein lokaler Sub-Agent fehl (inkl. Proxy-Verbindungsfehler
  während laufendem Task): sofortiger Retry auf Cloud-Claude ohne vorherigen
  lokalen Retry. Schlägt auch Cloud fehl: Orchestrator hält an, gibt Fehlerbericht aus.
  Schlägt ein Cloud-Sub-Agent fehl: 1 Retry auf Cloud, dann Eskalation.

- **FR-10:** Ist `local_agent.enabled = false` oder fehlt die Sektion in
  `config.yaml`: transparenter Fallback auf sequenziellen Single-Context-Cloud-Mode
  (SPEC-0035-Verhalten), Output kennzeichnet `[Fallback: Cloud-Only-Mode]`.

- **FR-11:** Proxy-Health-Check beim Start optional konfigurierbar
  (`local_agent.health_check: true`): GET auf `proxy_url/health` oder erster
  Ping-Request. Bei Fehler → sofortiger Fallback auf Cloud-Mode mit Warnung.

## 5. Konfigurationsschema

```yaml
# .sdd/config.yaml
local_agent:
  enabled: true
  proxy_url: "http://localhost:4000"    # LiteLLM oder kompatibler Anthropic-Proxy
  model: "llama3.1:8b"                  # Modellname wie beim Proxy registriert
  context_window: 131072                # Max. Context-Tokens des lokalen Modells
  context_reserve_tokens: 8192          # Reserviert für Model-Output
  max_parallel_local: 4                 # Max. parallele lokale Sub-Agenten
  max_parallel_cloud: 2                 # Max. parallele Cloud-Sub-Agenten
  api_key: "local-key"                  # Beliebiger String für Proxy-Auth
  health_check: true                    # Proxy-Ping vor erstem Task (optional)
```

## 6. User Stories

| ID    | Als …  | möchte ich …                                                        | um …                                                          |
|-------|--------|---------------------------------------------------------------------|---------------------------------------------------------------|
| US-01 | Boris  | `sdd implement SPEC-XXXX` starten und sehen welcher Task wo läuft  | Kosten und Routing nachvollziehen zu können                   |
| US-02 | Boris  | unabhängige Tasks parallel auf lokalen Modellen laufen lassen       | Implementierungszeit zu reduzieren ohne Cloud-Kosten          |
| US-03 | Boris  | bei zu großem Kontext automatisch auf Cloud-Claude eskalieren       | kein Task still scheitert weil das lokale Modell überfordert ist |
| US-04 | Boris  | den Proxy und das Modell in config.yaml konfigurieren               | zwischen Ollama, LM Studio und llama.cpp zu wechseln          |

## 7. Nicht-funktionale Anforderungen

| Kategorie      | Anforderung                                                                         |
|----------------|-------------------------------------------------------------------------------------|
| Performance    | Token-Zählung (FR-02) darf max. 200ms pro Task dauern (tiktoken ist lokal, kein API-Call) |
| Observability  | Jeder Task-Dispatch loggt: task_id, route (local/cloud), estimated_tokens, model   |
| Portabilität   | Fallback auf Cloud-Only wenn `local_agent` fehlt oder Proxy nicht erreichbar        |
| Security       | `api_key` erscheint nicht in Logs; Env-Var-Referenz `${ENV_VAR}` als Alternative  |
| Korrektheit    | Parallelität verletzt keine Task-Abhängigkeiten (DAG-Invariante)                   |

## 8. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: Kontextgeprüfte parallele Sub-Agenten-Delegation

  Scenario: Unabhängige Tasks laufen parallel lokal
    Given local_agent.enabled ist true und Proxy läuft
    And SPEC-XXXX hat 3 unabhängige Tasks mit kleinem Kontext
    When sdd implement SPEC-XXXX ausgeführt wird
    Then werden bis zu 4 LocalSubAgentProxy-Instanzen parallel gestartet
    And token-history enthält Einträge mit agent_type=local für jeden Task

  Scenario: Task zu groß für lokales Context-Window → Cloud
    Given local_agent.context_window ist 32768
    And Task-Kontext umfasst 40000 Tokens (Spec + Contracts + Code)
    When ContextSizeRoutingStrategy.route(task) aufgerufen wird
    Then gibt route "cloud" zurück
    And Output zeigt "[CLOUD: ...] (context too large)"

  Scenario: Lokaler Sub-Agent schlägt fehl → Cloud-Eskalation
    Given Task wird an LocalSubAgentProxy delegiert
    And LocalSubAgentProxy.execute() schlägt zweimal fehl
    When DagScheduler den Retry-Mechanismus ausführt
    Then wird Task an CloudSubAgentProxy übergeben
    And Orchestrator hält nur an wenn auch Cloud fehlschlägt

  Scenario: Fallback bei deaktiviertem local_agent
    Given local_agent.enabled ist false
    When sdd implement SPEC-XXXX ausgeführt wird
    Then läuft die Implementierung im Cloud-Only-Mode
    And Output zeigt "[Fallback: Cloud-Only-Mode]"

  Scenario: Abhängige Tasks laufen sequenziell
    Given Task-B hängt von Task-A ab
    When sdd implement SPEC-XXXX ausgeführt wird
    Then startet Task-B erst nachdem Task-A completed ist
    And keine parallele Ausführung von A und B findet statt
```

## 9. Contracts

| Contract-ID | Typ      | Was wird garantiert?                                                          |
|-------------|----------|-------------------------------------------------------------------------------|
| CON-0125    | behavior | `LlmRoutingStrategy.route()` — Routing-Entscheidung nach Context-Größe       |
| CON-0126    | behavior | `LocalSubAgentProxy.execute()` — Env-Override, Polymorphie, Fehler-Eskalation |
| CON-0127    | behavior | `DagScheduler.run()` — Abhängigkeitsreihenfolge, parallele Slots, Observer   |
| CON-0128    | data     | `local_agent`-Konfigurationsschema in `.sdd/config.yaml`                      |
| CON-0129    | data     | Token-History-Erweiterung: `agent_type` + `model` (koordiniert mit CON-0121) |

## 10. Tests

| Test-ID  | Level    | Was prüft der Test?                                                         |
|----------|----------|-----------------------------------------------------------------------------|
| TST-0147 | unit     | `ContextSizeRoutingStrategy.route()` — Grenzwerte, enabled-Flag, kein Netz |
| TST-0148 | unit     | `LocalSubAgentProxy.execute()` — Env-Override, api_key kein Log, Eskalation |
| TST-0149 | unit     | `DagScheduler` — Abhängigkeitsreihenfolge, Slot-Limits, Zyklus-Erkennung   |
| TST-0150 | contract | `local_agent`-Config-Schema — Pflichtfelder, Fallback, ${ENV_VAR}-Auflösung |
| TST-0151 | contract | Token-History `agent_type`/`model` — Schreiben, Lesen, Rückwärtskompatibilität |

## 11. Implementierungsreihenfolge

1. `sdd decompose` um Abhängigkeitskanten (`depends_on` pro Task) erweitern (FR-01)
2. `tiktoken`-Dependency + `ContextSizeEstimator` (FR-02)
3. `LlmRoutingStrategy`-Protocol + `ContextSizeRoutingStrategy` (FR-03)
4. `SubAgentProxy`-Protocol + `LocalSubAgentProxy` mit Env-Override (FR-04)
5. `DagScheduler` mit Observer-basierter Parallelitätssteuerung (FR-05)
6. Output-Formatierung pro Task: `[LOCAL/CLOUD: model] Task-Label` (FR-06)
7. `token-history`-Schema um `agent_type` + `model` erweitern (FR-07, SPEC-0035-Erweiterung)
8. `sdd calibrate` um Cloud/Lokal-Breakdown erweitern (FR-08)
9. Retry + Eskalationslogik (FR-09)
10. Fallback-Modus + Health-Check (FR-10, FR-11)
11. Contracts und Tests anlegen

## 12. Offene Fragen

- [x] Welche Code-Dateien werden in den Task-Kontext einbezogen?
      → Aus dem Decompose-Output (explizite Dateiliste pro Task, nicht heuristisch). FR-02 aktualisiert.
- [x] Soll `max_parallel` Cloud- und lokale Slots zusammenzählen oder getrennt
      konfigurierbar sein? → Getrennt: `max_parallel_local` + `max_parallel_cloud`. FR-05 + Config-Schema aktualisiert.
- [x] Verhalten bei Proxy-Verbindungsfehler während laufendem Task?
      → Sofortiger Cloud-Retry (kein lokaler Retry bei Verbindungsfehler). FR-09 aktualisiert.
- [x] Soll tiktoken ersetzbar sein (z.B. Ollama `tokenize`-Endpoint)?
      → Nein, tiktoken (cl100k_base) ist fest. Als Nicht-Ziel dokumentiert.

## 13. Änderungshistorie

| Datum      | Version | Autor      | Änderung            |
|------------|---------|------------|---------------------|
| 2026-06-05 | 0.1.0   | borisbrue  | Initiale Erstellung |
| 2026-06-05 | 0.2.0   | borisbrue  | Review-Findings eingearbeitet: Schema-Koordination SPEC-0011 (FR-07, ERROR), tiktoken-Utility-Sharing (FR-02), calibrate-Erweiterung statt Neudefinition (FR-08), Abgrenzungen SPEC-0008/SPEC-0013/SPEC-0016 in §1 + §3 |
