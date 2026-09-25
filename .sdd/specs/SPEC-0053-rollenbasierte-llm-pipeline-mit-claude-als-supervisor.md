---
id: SPEC-0053
title: "Rollenbasierte LLM-Pipeline mit Claude als Supervisor"
type: feature
status: draft
owner: "Boris"
created: 2026-09-25
updated: 2026-09-25
version: 0.2.0
priority: high
tags: [llm, roles, pipeline, local-llm, supervisor, token-tracking]
depends_on: [SPEC-0008, SPEC-0026, SPEC-0045, SPEC-0050, SPEC-0054]
contracts: []
tests: []
---

# Rollenbasierte LLM-Pipeline mit Claude als Supervisor

> **Status:** draft · **Owner:** Boris · **Version:** 0.2.0

## 1. Kontext & Motivation

Heute ist Claude in sdd-framer gleichzeitig Zerleger, Testautor, Implementierer, Reviewer und
Eskalationsziel. `TaskDecomposer` erzeugt fest einen `ClaudeCliCompletionProvider`
(`decompose.py:107-111`) und ignoriert die Config. `/sdd-implement` schreibt jeden RED-Test selbst
und übernimmt nach zwei lokalen Fehlversuchen die Implementierung. Lokale Modelle kommen nur über
`task_routing` für „einfache“ Tasks zum Zug (SPEC-0045).

Selbst gehostete Modelle (MLX/vLLM/Ollama, Qwen3.x, gpt-oss) liefern in BEFUND-modelle-2026-09-24
90–97 % auf isolierten Codeaufgaben. Die teure und knappe Ressource ist Claude. Sie soll nur noch dort
eingesetzt werden, wo Urteilsvermögen gebraucht wird: Freigaben, Eskalationsentscheidungen und die
Abnahme der Anforderungen.

Gleichzeitig sind die Rollen heute implizit: Prompts liegen als Inline-Strings in sieben Modulen
verteilt, Ein- und Ausgaben sind nicht als Vertrag definiert, und der Tokenverbrauch pro Rolle wird
nicht erfasst (Code-Gen liefert gar keine Usage, `claude-cli` liefert `None`, obwohl das JSON-Envelope
Usage enthält). Damit lässt sich weder sagen, welches Modell welche Rolle gut erfüllt, noch eine
Rolle gezielt verbessern (→ SPEC-0055) oder vergleichen (→ SPEC-0056).

## 2. Zielsetzung

**Primärziel:** Jeder LLM-Schritt der Implementierung ist eine explizit definierte Rolle mit Vertrag,
eigenem Modell und Messung; Claude ist ausschließlich Supervisor und schreibt keinen Code.

**Erfolgskriterien (messbar):**
- [ ] Eine Spec lässt sich mit `sdd pipeline run SPEC-XXXX` von Decompose bis Finalize umsetzen,
      ohne dass ein Claude-Aufruf Produktions- oder Testcode erzeugt (prüfbar über das Run-Protokoll:
      alle Datei-Schreibvorgänge stammen aus Rollen ≠ `supervisor`).
- [ ] `decomposer`, `test_author`, `implementer`, `reviewer` und `supervisor` sind je auf ein
      beliebiges konfiguriertes Modell setzbar, inklusive Thinking-Modus und Reasoning-Budget.
- [ ] Für jeden LLM-Aufruf der Pipeline existiert ein Usage-Datensatz mit Rolle, Modell, Input-,
      Output- und Reasoning-Tokens, Dauer, Versuch und Ergebnis.
- [ ] Claude-Tokens pro umgesetzter Spec sinken gegenüber `/sdd-implement` auf der Benchmark-Suite
      (SPEC-0056) um ≥ 70 % bei nicht schlechterem Qualitätsscore (SPEC-0054).
- [ ] Ohne `llm.roles`-Block verhält sich sdd-framer exakt wie bisher (Rückwärtskompatibilität).

**Nicht-Ziele (explizit):**
- Kein Ersatz von `/sdd-implement`; der interaktive Weg bleibt bestehen.
- Kein automatisches Hosting, Laden oder Umschalten von Modellen auf dem LLM-Server.
- Keine Parallelisierung über `task_routing.max_concurrent` hinaus.
- Die Evals (SPEC-0055) und der Benchmark (SPEC-0056) sind eigene Specs.

## 3. Architektur & Design Patterns

### Rollen als Daten + Strategy für den Provider
Eine Rolle ist eine Datei `.sdd/roles/<rolle>.md`. Die Frontmatter definiert den Vertrag, der Body
den System-Prompt:

```yaml
---
role: decomposer
version: 1.2.0
purpose: "Zerlegt eine freigegebene Spec in testbare, abhängigkeitsgeordnete Tasks."
inputs: [spec, contracts, agents_md, repo_map]      # geschlossene Liste, s. FR-03
output_schema: contracts/data/role-decomposer-output.schema.json
defaults: { thinking: true, max_output_tokens: 16000, temperature: 0.6 }
checks: [json_schema, fr_coverage, acyclic, deps_resolvable, test_file_per_code_task]
---
<System-Prompt>
```

Welches Modell eine Rolle spielt, steht nicht in der Rollendatei, sondern in `config.yaml`
(`llm.roles.<rolle>`). Der Provider wird per Strategy aufgelöst (bestehende Factory, erweitert).
Damit sind Rollendefinition (trainierbar, SPEC-0055) und Modellwahl (benchmarkbar, SPEC-0056)
unabhängig voneinander.

→ [Refactoring Guru: Strategy](https://refactoring.guru/design-patterns/strategy)

### Template Method: `RoleRunner`
Jeder Rollenaufruf durchläuft dieselben Schritte: Kontext zusammenstellen → Prompt rendern → LLM
aufrufen → Ausgabe extrahieren → gegen `output_schema` validieren → deterministische `checks`
ausführen → Usage persistieren. Rollen überschreiben nur Kontextaufbau und Ergebnisanwendung.
Ungültige Ausgaben sind ein gezählter Fehlversuch, kein Absturz.

→ [Refactoring Guru: Template Method](https://refactoring.guru/design-patterns/template-method)

### Mediator: `PipelineSupervisor`
Die Rollen kennen einander nicht. Der Mediator steuert den Ablauf, reicht Artefakte weiter und ruft
die Rolle `supervisor` nur an definierten Entscheidungspunkten (FR-08) auf.

→ [Refactoring Guru: Mediator](https://refactoring.guru/design-patterns/mediator)

### Chain of Responsibility: deterministische Gates vor jedem Urteil
Zwischen den Rollen laufen Gates aus SPEC-0054 (Tests, Lint, Architekturregeln, Pfadschutz). Der
Supervisor bekommt Fakten (Gate-Ergebnisse, Diffs, Fehlerausgaben), keine Selbstauskünfte der Modelle.

### State: Task-Lebenszyklus
`pending → red → green → reviewed → done`, Nebenpfade `retry`, `reassigned`, `redecompose`, `halted`.
Jeder Übergang wird mit Rolle und Grund im Run-Protokoll festgehalten.

### Ablauf

```
decomposer ──► [Gates: Schema, FR-Abdeckung, Zyklen] ──► supervisor: Freigabe Zerlegung (S1)
   ▲                                                             │
   └──────────── Überarbeitung mit Supervisor-Begründung ◄──────┤ (max. n Runden)
                                                                 ▼
für jeden Task in Abhängigkeitswellen:
  test_author ─► [Gate: Test ist RED] ─► implementer ─► [Gates: GREEN, Lint, Architektur, Pfade]
       ─► reviewer ─► pass: done
                    └► fail/Gate-Fehler nach k Versuchen ─► supervisor: Eskalation (S2)
                           retry_with_hint | reassign(model) | redecompose | halt
Abschluss: [Gates: Regression, Holdouts, FR-Erfüllung] ─► supervisor: Abnahme (S3) ─► finalize
```

## 4. Funktionale Anforderungen

- **FR-01:** Es gibt die Rollen `decomposer`, `test_author`, `implementer`, `reviewer` und
  `supervisor`. Jede ist als Datei `.sdd/roles/<rolle>.md` definiert, mit Frontmatter nach dem
  Schema `contracts/data/role-definition.schema.json` und dem System-Prompt als Body.
- **FR-02:** `sdd init` und `sdd upgrade` installieren die Default-Rollen aus dem Blueprint.
  `sdd upgrade` überschreibt eine lokal geänderte Rolle nicht, sondern legt die neue Version als
  `<rolle>.md.new` daneben und meldet das (gleiches Verhalten wie bei Skills mit `--force-skills`).
- **FR-03:** Die Eingaben einer Rolle stammen aus einer geschlossenen Liste von Kontextquellen
  (`spec`, `contracts`, `agents_md`, `repo_map`, `task`, `test_file`, `test_output`, `diff`,
  `gate_results`, `review`, `history`). Jede Quelle hat ein konfigurierbares Tokenbudget. Unbekannte
  Quellen sind ein Validierungsfehler. `.sdd/holdout/` ist nie eine Quelle.
- **FR-04:** `llm.roles.<rolle>` in `config.yaml` akzeptiert `provider`, `model`, `base_url`,
  `api_key`, `temperature`, `top_p`, `max_output_tokens`, `thinking` (bool),
  `reasoning_effort` (`low|medium|high`, falls vom Server unterstützt) und `timeout_seconds`.
  Auflösung: `llm.roles.<rolle>` → bisheriger Komponentenblock (`decomposer`→`completion`,
  `implementer`/`test_author`→`orchestrator`, `reviewer`/`supervisor`→`evaluator`) → Builtin
  `claude-cli`. `sdd config validate` (SPEC-0052) prüft den Block.
- **FR-05:** `TaskDecomposer` holt seinen Provider über die Rolle `decomposer` statt fest über
  `ClaudeCliCompletionProvider`. Der Prompt kommt aus `.sdd/roles/decomposer.md`. Jeder Task
  bekommt das neue Feld `fr_ids` (Liste der abgedeckten FRs). Tasks ohne `fr_ids` sind nur für
  `type: config|doc` zulässig.
- **FR-06:** Alle Rollenaufrufe liefern ein `RoleResult` mit Ausgabe, `UsageMetadata` und
  Metadaten. `UsageMetadata` bekommt `reasoning_tokens`, `finish_reason` und `latency_ms`.
  - `openai-compat` liest `usage.completion_tokens_details.reasoning_tokens`, falls vorhanden.
  - `CodeGenProvider.generate` gibt Usage zurück.
  - `claude-cli` parst die Usage aus dem `--output-format json`-Envelope; `usage: None` entfällt
    damit für den keyfreien Betrieb.
- **FR-07:** Jeder Rollenaufruf schreibt einen Datensatz in `token_usage` mit den neuen Spalten
  `role`, `run_id`, `attempt`, `reasoning_tokens`, `outcome` (`ok|invalid_output|gate_failed|
  rejected|error`) und `role_version`. Die Migration ist additiv; bestehende Auswertungen
  (`token-history`, `estimate`) funktionieren unverändert.
- **FR-08:** Die Rolle `supervisor` entscheidet ausschließlich an drei Punkten und antwortet mit
  einem Entscheidungsobjekt nach `contracts/data/supervisor-decision.schema.json`:
  - **S1 Zerlegung:** `approve` oder `revise(begründung)`. Nach `max_revisions` (Default 2)
    Runden ohne Freigabe hält die Pipeline an.
  - **S2 Eskalation:** Ein Task scheitert nach `max_attempts` (Default 3) an Gates oder Review.
    Antworten: `retry_with_hint(text)`, `reassign(rolle, modell)`, `redecompose(begründung)`
    oder `halt(begründung)`.
  - **S3 Abnahme:** Nach allen Tasks und Abschluss-Gates gibt der Supervisor pro FR `erfüllt`,
    `teilweise` oder `fehlt` mit Beleg (Datei/Test) an. Ein `fehlt` blockiert Finalize.
- **FR-09:** Der Supervisor schreibt keine Dateien. Seine Ausgabe ist ausschließlich das
  Entscheidungsobjekt; `hint`-Texte werden dem nächsten Rollenaufruf als Kontextquelle `history`
  übergeben. Der Pfadschutz lehnt jeden Schreibversuch mit Rolle `supervisor` ab.
  Die bisherige Claude-Code-Eskalation (`claude (escalated)`) ist nur mit
  `pipeline.allow_supervisor_implementation: true` erreichbar (Default `false`) und wird im Report
  gesondert ausgewiesen.
- **FR-10:** `test_author` erzeugt pro Code-Task den Test. Das Gate prüft, dass der Test vor der
  Implementierung **fehlschlägt**, und zwar aus dem erwarteten Grund. Das Gate ist sprachneutral:
  Es führt die Testsonde aus SPEC-0054 aus und wertet das JUnit-Ergebnis aus. Der neue Test muss
  vorhanden sein und `failure` oder `error` melden. Bricht die Sonde ohne JUnit-Ergebnis ab (z. B.
  Syntax- oder Compilefehler im Test selbst), gilt der Test als ungültig. Danach darf `implementer`
  die Testdatei nicht mehr ändern (Pfadschutz auf `test_file`).
- **FR-11:** `reviewer` bekommt Diff, Task, betroffene FRs, Contracts, AGENTS.md-Regeln und die
  Gate-Ergebnisse aus SPEC-0054. Er antwortet mit `pass` oder `fail` und je Befund Kategorie
  (`requirement|architecture|quality|test`), Datei, Zeile und Begründung.
- **FR-12:** `sdd pipeline run SPEC-XXXX [--dry-run] [--resume RUN_ID] [--max-tasks N]` führt den
  Ablauf aus Abschnitt 3 aus. Voraussetzung ist Status `approved`; der Befehl ruft `sdd start` bzw.
  dessen Logik auf. Das Run-Protokoll liegt unter `.sdd/runs/<SPEC>/<run_id>/`: `run.json`
  (Konfiguration inkl. Modell und Rollenversion je Rolle), `events.jsonl` (jeder Übergang, jeder
  Rollenaufruf) und `decisions.jsonl` (Supervisor-Entscheidungen mit Begründung).
- **FR-13:** `--dry-run` führt nur `decomposer` und S1 aus und gibt Tasks, Tokenverbrauch und die
  geschätzte Rollenverteilung aus, ohne Code zu schreiben.
- **FR-14:** `sdd pipeline report RUN_ID` zeigt pro Rolle Aufrufe, Tokens (in/out/reasoning),
  Dauer, Fehlversuche und Supervisor-Eingriffe sowie den Anteil der Claude-Tokens am Gesamtverbrauch.
- **FR-15:** `llm.roles.supervisor.provider` akzeptiert zusätzlich `session`: Claude Code im Dialog
  ist der Supervisor. An jedem Entscheidungspunkt S1–S3 schreibt die Pipeline eine
  Entscheidungsanfrage nach `.sdd/runs/<SPEC>/<run_id>/pending-decision.json`. Sie enthält Punkt,
  Fakten (Gate-Ergebnisse, Diffs, Fehlerausgaben, Tokenstand) und die zulässigen Antworten. Danach
  wartet die Pipeline mit Status `awaiting_supervisor` und beendet sich mit Exit-Code 3.
  `sdd pipeline decide RUN_ID --json '<entscheidung>'` validiert die Antwort gegen
  `supervisor-decision.schema.json`, protokolliert sie in `decisions.jsonl` und setzt den Run fort.
  `sdd pipeline status RUN_ID` zeigt die offene Anfrage an.
- **FR-16:** Ein neuer Skill `/sdd-supervise SPEC-XXXX` startet den Run mit
  `supervisor.provider: session` und führt Claude Code durch die Schleife „Run fortsetzen →
  Anfrage lesen → entscheiden → `sdd pipeline decide`“. Der Skill legt Claudes Rolle ausdrücklich
  fest:
  - keine Edits an Code, Tests, Specs oder Contracts;
  - Entscheidungen nur auf Basis der Fakten aus der Anfrage, bei Bedarf ergänzt um lesenden Zugriff
    auf das Repo;
  - jede Entscheidung mit Begründung und Beleg;
  - dem Nutzer vorgelegt werden `halt` sowie jede S3-Abnahme mit `teilweise` oder `fehlt`.

  Für headless Läufe (CI, Benchmark) bleibt `claude-cli` der Default.

## 5. Nicht-funktionale Anforderungen

| Kategorie       | Anforderung                                                                      |
|-----------------|----------------------------------------------------------------------------------|
| Nachvollziehbarkeit | Jeder Rollenaufruf ist aus `events.jsonl` mit Prompt-Hash, Rollenversion, Modell und Usage rekonstruierbar. |
| Robustheit      | Ein nicht erreichbarer Modellserver führt zu `outcome: error` und S2, nicht zum Abbruch des Runs. `--resume` setzt nach dem letzten abgeschlossenen Task fort. |
| Sicherheit      | Kein Rollen-Output schreibt nach `.sdd/`, `specs/`, `contracts/` oder `.sdd/holdout/` (bestehender Pfadschutz aus `openai_compat.py` gilt für alle Provider). API-Keys erscheinen nicht in Logs oder `run.json`. |
| Keyfreiheit     | Default-Supervisor ist `claude-cli`; kein Default verlangt `ANTHROPIC_API_KEY`.   |
| Performance     | Der Overhead von Gates und Protokoll liegt pro Task unter 5 s, Testlaufzeit nicht eingerechnet. |

## 6. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: Rollenbasierte Pipeline

  Scenario: Decompose über ein Thinking-Modell
    Given llm.roles.decomposer zeigt auf ein openai-compat-Modell mit thinking: true
    When ich "sdd pipeline run SPEC-0900 --dry-run" ausführe
    Then enthält .sdd/tasks/SPEC-0900.json Tasks mit fr_ids
    And token_usage enthält einen Datensatz mit role=decomposer und reasoning_tokens > 0
    And es wurde kein claude-Prozess für die Zerlegung gestartet

  Scenario: Supervisor verlangt Überarbeitung
    Given der decomposer liefert Tasks, die FR-03 nicht abdecken
    When das Gate fr_coverage fehlschlägt
    Then ruft die Pipeline den decomposer erneut mit der Gate-Meldung auf
    And ruft den supervisor erst auf, wenn alle Gates grün sind

  Scenario: Supervisor schreibt keinen Code
    Given ein Task scheitert dreimal am Review
    When der supervisor mit "reassign(implementer, qwen3.8-27b)" antwortet
    Then bearbeitet das Modell qwen3.8-27b den Task in der Rolle implementer
    And decisions.jsonl enthält die Entscheidung mit Begründung
    And kein Datei-Schreibvorgang des Runs trägt role=supervisor

  Scenario: Rückwärtskompatibilität
    Given config.yaml enthält keinen Block llm.roles
    When ich "sdd decompose SPEC-0900" ausführe
    Then wird der Provider aus llm.completion verwendet
```

## 7. Edge Cases & Fehlerfälle

- Das Thinking-Modell schöpft `max_output_tokens` im Reasoning aus und liefert leeren Content
  (`finish_reason=length`, bekannt vom MLX-Server): `outcome: invalid_output`, der Retry läuft mit
  erhöhtem Budget (×1,5, einmalig), danach S2.
- Server ignoriert `enable_thinking` (MLX): Die Rollenkonfiguration erlaubt einen alternativen
  Modellnamen (z. B. `:no-think`); `sdd config test-llm --role <rolle>` meldet, ob Reasoning-Tokens
  zurückkommen.
- Der decomposer erzeugt einen Test-Task für einen Contract, der nicht existiert: Das Gate
  `deps_resolvable` schlägt fehl.
- `test_author` schreibt einen Test, der schon ohne Implementierung grün ist: Das RED-Gate schlägt
  fehl, und der Test wird verworfen.
- `implementer` ändert eine Datei außerhalb der erlaubten Pfade des Tasks: Der Schreibvorgang wird
  abgelehnt und als `gate_failed` gewertet.
- Der Supervisor liefert eine ungültige Entscheidung: Nach einer Wiederholung hält der Run mit
  `halt` an. Der Supervisor wird nie „erraten“.
- LiteLLM- oder Proxy-Response-Cache: Jeder Aufruf trägt einen Nonce im System-Prompt-Kommentar.

## 8. Contracts (was wird garantiert)

| Contract-ID | Typ      | Was wird garantiert?                                                  |
|-------------|----------|-----------------------------------------------------------------------|
| CON-XXXX    | data     | `role-definition.schema.json`: Frontmatter einer Rollendatei          |
| CON-XXXX    | data     | Ausgabeschemata je Rolle (decomposer, test_author, implementer, reviewer) |
| CON-XXXX    | data     | `supervisor-decision.schema.json` für S1–S3                           |
| CON-XXXX    | data     | Run-Protokoll: `run.json`, `events.jsonl`, `decisions.jsonl`          |
| CON-XXXX    | data     | `token_usage`-Erweiterung (Spalten, Migration)                        |
| CON-XXXX    | behavior | Pipeline-Ablauf und Entscheidungspunkte (Gherkin aus Abschnitt 6)     |
| CON-0096    | data     | Task-Schema 0.3.0: Feld `fr_ids`                                      |

## 9. Tests (wie wird verifiziert)

| Test-ID  | Level       | Was prüft der Test?                                                   |
|----------|-------------|-----------------------------------------------------------------------|
| TST-XXXX | unit        | Provider-Auflösung je Rolle inkl. Fallback-Kette (FR-04)              |
| TST-XXXX | unit        | `RoleRunner`: Schema-Validierung, `invalid_output`, Usage-Persistenz  |
| TST-XXXX | unit        | Usage-Parsing: reasoning_tokens (openai-compat), claude-cli-Envelope  |
| TST-XXXX | integration | Pipeline mit Fake-Providern: S1/S2/S3, Pfadschutz Supervisor, RED-Gate |
| TST-XXXX | acceptance  | Gherkin-Szenarien aus Abschnitt 6                                     |

## 10. Offene Fragen

- [x] Claude Code im Dialog als Supervisor → ja, in dieser Spec (FR-15, FR-16; entschieden
      2026-09-25).
- [ ] Ersetzt `sdd pipeline run` den Befehl `sdd task-loop` (SPEC-0045), oder bleibt `task-loop`
      als schlanker Pfad bestehen? Vorschlag: `task-loop` wird zu `pipeline run` mit
      Default-Rollenbelegung und bleibt als Alias.
- [ ] Soll der `reviewer` bei Modellgleichheit mit dem `implementer` gewarnt werden, damit kein
      Modell sich selbst reviewt?
- [ ] Die uncommittete Arbeit an SPEC-0045 (`Task.executor`, Eskalation im `loop_controller`)
      muss vor der Umsetzung gemergt sein.

## 11. Änderungshistorie

| Datum      | Version | Autor         | Änderung            |
|------------|---------|---------------|---------------------|
| 2026-09-25 | 0.1.0   | Boris, Claude | Initiale Erstellung |
| 2026-09-25 | 0.2.0   | Boris, Claude | Supervisor im Dialog (`session`, `/sdd-supervise`) verbindlich; RED-Gate sprachneutral über JUnit |
