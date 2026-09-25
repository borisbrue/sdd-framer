---
id: SPEC-0053
title: "Rollenbasierte LLM-Pipeline mit Claude als Supervisor"
type: feature
status: draft
owner: "Boris"
created: 2026-09-25
updated: 2026-09-25
version: 0.5.0
priority: high
tags: [llm, roles, pipeline, local-llm, supervisor]
depends_on: [SPEC-0008, SPEC-0011, SPEC-0026, SPEC-0045, SPEC-0050, SPEC-0054, SPEC-0060]
contracts: [CON-0199, CON-0200, CON-0201, CON-0202, CON-0203, CON-0204, CON-0205]
tests: []
---

# Rollenbasierte LLM-Pipeline mit Claude als Supervisor

> **Status:** draft · **Owner:** Boris · **Version:** 0.5.0

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
verteilt, Ein- und Ausgaben sind nicht als Vertrag definiert, und Schreibrechte hängen an einem
einzelnen Provider (`openai_compat.py`). Damit lässt sich weder sagen, welches Modell welche Rolle
gut erfüllt, noch eine Rolle gezielt verbessern (→ SPEC-0055) oder vergleichen (→ SPEC-0056).

### Abgrenzung zu bestehenden Specs
- **SPEC-0008/SPEC-0050 (Provider-Factory):** Rollen führen keinen zweiten Weg zur Modellwahl ein.
  `llm.roles.<rolle>` ist ein weiterer Schlüssel derselben Factory (FR-04).
- **SPEC-0011 und SPEC-0060 (Tokenverbrauch):** Die Usage-Erfassung aller Provider regelt SPEC-0060
  und schreibt in die bestehende Tabelle `token_usage`. Diese Spec liefert nur den Rollenkontext
  (Rolle, Run, Versuch, Ergebnis, Rollenversion).
- **SPEC-0004 und SPEC-0007 (Orchestrator, Execute-Button der Web-UI) sowie SPEC-0045
  (`task-loop`):** Wie diese Pfade auf `sdd pipeline` abgebildet werden, regelt SPEC-0058.
- **SPEC-0005 (Analyzer):** Der Analyzer ist keine Rolle der Implementierungs-Pipeline und bleibt
  eine Provider-Komponente.

## 2. Zielsetzung

**Primärziel:** Jeder LLM-Schritt der Implementierung ist eine explizit definierte Rolle mit Vertrag,
eigenem Modell und Messung; Claude ist ausschließlich Supervisor und schreibt keinen Code.

**Erfolgskriterien (messbar):**
- [ ] Eine Spec lässt sich mit `sdd pipeline run SPEC-XXXX` von Decompose bis Finalize umsetzen,
      ohne dass ein Claude-Aufruf Produktions- oder Testcode erzeugt (prüfbar über das Run-Protokoll:
      alle Datei-Schreibvorgänge stammen aus Rollen ≠ `supervisor`).
- [ ] `decomposer`, `test_author`, `implementer`, `reviewer` und `supervisor` sind je auf ein
      beliebiges konfiguriertes Modell setzbar, inklusive Thinking-Modus und Reasoning-Budget.
- [ ] Jeder Rollenaufruf erzeugt einen Usage-Datensatz (SPEC-0060) mit Rollenkontext.
- [ ] Ein Run lässt sich an jedem Entscheidungspunkt und nach jedem abgeschlossenen Task abbrechen
      und mit `--resume` ohne Verlust fortsetzen.
- [ ] Claude-Tokens pro umgesetzter Spec sinken gegenüber `/sdd-implement` auf der Benchmark-Suite
      (SPEC-0056) um ≥ 70 % bei nicht schlechterem Qualitätsscore (SPEC-0054).
- [ ] Ohne `llm.roles`-Block verhält sich sdd-framer exakt wie bisher (Rückwärtskompatibilität).

**Nicht-Ziele (explizit):**
- Kein Ersatz von `/sdd-implement`; der interaktive Weg bleibt bestehen.
- Kein automatisches Hosting, Laden oder Umschalten von Modellen auf dem LLM-Server.
- Keine Parallelisierung über `task_routing.max_concurrent` hinaus.
- Keine Korrektur der Usage-Erfassung der Provider (→ SPEC-0060).
- Keine Ablösung von `task-loop`, `orchestrate`, `distribute` oder des Web-Execute-Buttons
  (→ SPEC-0058).
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
legacy_component: completion                          # Fallback ohne llm.roles.<rolle>
---
<System-Prompt>
```

Welches Modell eine Rolle spielt, steht nicht in der Rollendatei, sondern in `config.yaml`
(`llm.roles.<rolle>`). Der Provider wird per Strategy über die bestehende Factory (SPEC-0008)
aufgelöst. Auch der Fallback auf einen alten Komponentenblock ist Teil der Rollendaten
(`legacy_component`), sodass eine neue Rolle keine Codeänderung an der Auflösung braucht.

→ [Refactoring Guru: Strategy](https://refactoring.guru/design-patterns/strategy)

### Template Method: `RoleRunner`
Jeder Rollenaufruf durchläuft dieselben Schritte: Kontext zusammenstellen → Prompt rendern (mit
Nonce) → LLM aufrufen → Ausgabe extrahieren → gegen `output_schema` validieren → Rollen-`checks`
ausführen → Usage mit Rollenkontext an SPEC-0060 übergeben. Rollen überschreiben nur Kontextaufbau
und Ergebnisanwendung. Ungültige Ausgaben sind ein gezählter Fehlversuch, kein Absturz.

**Grenze Rollen-Checks ↔ Gates:** Rollen-`checks` prüfen ausschließlich die *Ausgabe* der Rolle
(Schema, Struktur, Vollständigkeit gegenüber ihrer Eingabe, z. B. `fr_coverage` der Zerlegung).
Gates (SPEC-0054) prüfen den *Projektzustand* nach dem Anwenden (Tests, Lint, Architektur). Rollen-
Checks laufen im `RoleRunner`, Gates im Mediator.

→ [Refactoring Guru: Template Method](https://refactoring.guru/design-patterns/template-method)

### Mediator: `PipelineSupervisor`
Die Rollen kennen einander nicht. Der Mediator steuert den Ablauf, reicht Artefakte weiter, wendet
die `PathPolicy` auf jeden Schreibvorgang an und holt an den Entscheidungspunkten S1–S3 eine
Entscheidung ein.

→ [Refactoring Guru: Mediator](https://refactoring.guru/design-patterns/mediator)

### Command: Supervisor-Entscheidungen
Jede Entscheidung ist ein serialisierbares Objekt (`approve`, `revise`, `retry_with_hint`,
`reassign`, `redecompose`, `halt`, `accept_frs`), validiert gegen
`supervisor-decision.schema.json`. Der Supervisor führt nichts aus; der Mediator führt das Command
aus und protokolliert es in `decisions.jsonl`. Dadurch funktionieren der Dialogmodus, `--resume`
und die Protokollierung über denselben Mechanismus, egal wer entscheidet.

→ [Refactoring Guru: Command](https://refactoring.guru/design-patterns/command)

### Entscheidungsquelle und fortsetzbarer Zustandsautomat
Der Run ist ein Zustandsautomat, dessen Zustand nach jedem Übergang in `state.json` gespeichert
wird. An jedem Entscheidungspunkt wird zuerst die Anfrage persistiert
(`pending-decision.json`), dann eine `DecisionSource` gefragt. Jede Quelle erfüllt denselben
Vertrag: Sie liefert entweder ein Command oder `Pending(request)`.

| Modus (`llm.roles.supervisor.mode`) | Quelle | Verhalten |
|-------------------------------------|--------|-----------|
| `inline` (Default) | Supervisor-Rolle über ihren Provider | liefert sofort ein Command |
| `session` | Claude Code im Dialog | liefert `Pending`; der Run hält mit Exit 3 an und wird mit `sdd pipeline decide` fortgesetzt |

Der Provider der Supervisor-Rolle wird nur im Modus `inline` gebraucht.

### PathPolicy
Eine anbieterunabhängige Regel entscheidet für jeden Schreibvorgang anhand von Rolle, Task und
erlaubten Pfaden, ob er zulässig ist. Der Mediator wendet sie an; Provider (auch
`openai_compat.py`) nutzen sie nur und enthalten keine eigenen Pfadregeln mehr.

### State: Task-Lebenszyklus
`pending → red → green → reviewed → done`, Nebenpfade `retry`, `reassigned`, `redecompose`, `halted`.
Jeder Übergang wird mit Rolle und Grund in `events.jsonl` und `state.json` festgehalten.

### Ablauf

```
decomposer ──► [Rollen-Checks: Schema, FR-Abdeckung, Zyklen] ──► S1 Freigabe Zerlegung
   ▲                                                                   │
   └──────────── Überarbeitung mit Begründung (revise) ◄──────────────┤ (max. n Runden)
                                                                       ▼
für jeden Task in Abhängigkeitswellen:
  test_author ─► [Gate: Test ist RED] ─► implementer ─► [Gates: GREEN, Lint, Architektur]
       ─► reviewer ─► pass: done                         (jeder Schreibvorgang: PathPolicy)
                    └► fail/Gate-Fehler nach k Versuchen ─► S2 Eskalation
                           retry_with_hint | reassign(model) | redecompose | halt
Abschluss: [Gates: Regression, Holdouts, FR-Erfüllung] ─► S3 Abnahme ─► finalize
```

## 4. Funktionale Anforderungen

- **FR-01:** Es gibt die Rollen `decomposer`, `test_author`, `implementer`, `reviewer` und
  `supervisor`. Jede ist als Datei `.sdd/roles/<rolle>.md` definiert, mit Frontmatter nach dem
  Schema `contracts/data/role-definition.schema.json` (inklusive `legacy_component`) und dem
  System-Prompt als Body.
- **FR-02:** `sdd init` und `sdd upgrade` installieren die Default-Rollen aus dem Blueprint.
  `sdd upgrade` überschreibt eine lokal geänderte Rolle nicht, sondern legt die neue Version als
  `<rolle>.md.new` daneben und meldet das.
- **FR-03:** Die Eingaben einer Rolle stammen aus einer geschlossenen Liste von Kontextquellen
  (`spec`, `contracts`, `agents_md`, `repo_map`, `task`, `test_file`, `test_output`, `diff`,
  `gate_results`, `review`, `history`). Jede Quelle hat ein konfigurierbares Tokenbudget. Unbekannte
  Quellen sind ein Validierungsfehler. `.sdd/holdout/` ist nie eine Quelle.
- **FR-04:** `llm.roles.<rolle>` ist ein Schlüssel der Provider-Factory (SPEC-0008) und akzeptiert
  `provider`, `model`, `base_url`, `api_key`, `temperature`, `top_p`, `max_output_tokens`,
  `thinking`, `reasoning_effort` (`low|medium|high`) und `timeout_seconds`, für den Supervisor
  zusätzlich `mode` (FR-15). Auflösung: `llm.roles.<rolle>` → Komponentenblock aus
  `legacy_component` der Rollendatei → Builtin `claude-cli`. `sdd config validate` prüft den Block
  und warnt:
  - bei Parametern, die der gewählte Provider ignoriert (z. B. `base_url` bei `claude-cli`);
  - wenn `reviewer` dasselbe Modell (Endpunkt und Modellname) nutzt wie `implementer` oder
    `test_author` („Modell reviewt seine eigene Arbeit“). Diese Warnung erscheint auch beim Start
    von `sdd pipeline run`, in `run.json` und im Report; sie blockiert nicht. Bei
    `by_complexity`-Belegungen (SPEC-0058) wird je Stufe verglichen.
- **FR-05:** `TaskDecomposer` holt seinen Provider über die Rolle `decomposer` statt fest über
  `ClaudeCliCompletionProvider`. Der Prompt kommt aus `.sdd/roles/decomposer.md`. Jeder Task
  bekommt das neue Feld `fr_ids` (Liste der abgedeckten FRs). Tasks ohne `fr_ids` sind nur für
  `type: config|doc` zulässig.
- **FR-06:** Der `RoleRunner` liefert für jeden Aufruf ein `RoleResult` (Ausgabe, Usage,
  Metadaten). Er übergibt die Usage an die Erfassung aus SPEC-0060 mit dem Rollenkontext `role`,
  `run_id`, `attempt`, `outcome` (`ok|invalid_output|gate_failed|rejected|error`) und
  `role_version`. Bei `finish_reason=length` ohne verwertbaren Inhalt wiederholt er einmalig mit
  dem 1,5-fachen Ausgabebudget. Jeder Prompt trägt einen Nonce gegen Proxy-Caches.
- **FR-07:** **PathPolicy.** Jeder Schreibvorgang einer Rolle läuft über eine anbieterunabhängige
  `PathPolicy` (eigener Contract). Sie lehnt ab:
  - jeden Schreibvorgang der Rolle `supervisor`;
  - Schreibvorgänge nach `.sdd/**`, `specs/**`, `contracts/**` und `.sdd/holdout/**`;
  - Änderungen des `implementer` an der `test_file` seines Tasks;
  - Pfade außerhalb der für den Task erlaubten Pfade.

  Abgelehnte Schreibvorgänge zählen als `gate_failed`. `openai_compat.py` nutzt dieselbe Policy
  und behält keine eigene Pfadregel.
- **FR-08:** Die Supervisor-Entscheidungen sind Commands nach
  `contracts/data/supervisor-decision.schema.json`, die der Mediator ausführt:
  - **S1 Zerlegung:** `approve` oder `revise(begründung)`. Nach `max_revisions` (Default 2)
    Runden ohne Freigabe hält die Pipeline an.
  - **S2 Eskalation:** Ein Task scheitert nach `max_attempts` (Default 3) an Gates oder Review.
    Antworten: `retry_with_hint(text)`, `reassign(rolle, modell)`, `redecompose(begründung)`
    oder `halt(begründung)`.
  - **S3 Abnahme:** `accept_frs` mit je FR `erfüllt`, `teilweise` oder `fehlt` samt Beleg
    (Datei/Test). Ein `fehlt` blockiert Finalize.

  Eine ungültige Entscheidung wird einmal neu angefragt, danach hält der Run mit `halt` an.
- **FR-09:** Der Supervisor schreibt keine Dateien (durchgesetzt über FR-07). `hint`-Texte werden
  dem nächsten Rollenaufruf als Kontextquelle `history` übergeben. Die bisherige
  Claude-Code-Eskalation (`claude (escalated)`) ist nur mit
  `pipeline.allow_supervisor_implementation: true` erreichbar (Default `false`) und wird im Report
  gesondert ausgewiesen.
- **FR-10:** `test_author` erzeugt pro Code-Task den Test. Das Gate prüft, dass der Test vor der
  Implementierung **fehlschlägt**, und zwar aus dem erwarteten Grund. Das Gate ist sprachneutral:
  Es führt die Testsonde aus SPEC-0054 aus und wertet das JUnit-Ergebnis aus. Der neue Test muss
  vorhanden sein und `failure` oder `error` melden. Bricht die Sonde ohne JUnit-Ergebnis ab, gilt
  der Test als ungültig.
- **FR-11:** `reviewer` bekommt Diff, Task, betroffene FRs, Contracts, AGENTS.md-Regeln und die
  Gate-Ergebnisse aus SPEC-0054. Er antwortet mit `pass` oder `fail` und je Befund Kategorie
  (`requirement|architecture|quality|test`), Datei, Zeile und Begründung.
- **FR-12:** `sdd pipeline run SPEC-XXXX [--dry-run] [--resume RUN_ID] [--max-tasks N]` führt den
  Ablauf aus Abschnitt 3 aus. Voraussetzung ist Status `approved`. Unter
  `.sdd/runs/<SPEC>/<run_id>/` liegen:
  - `run.json`: Konfiguration inklusive Modell und Rollenversion je Rolle;
  - `state.json`: aktueller Zustand des Automaten, nach jedem Übergang geschrieben;
  - `events.jsonl`: jeder Übergang und jeder Rollenaufruf;
  - `decisions.jsonl`: jede Supervisor-Entscheidung mit Begründung;
  - `pending-decision.json`: die offene Entscheidungsanfrage, solange eine besteht.

  `--resume` setzt am gespeicherten Zustand fort, auch nach Abbruch mitten in einem Task (der Task
  beginnt dann mit dem nächsten Versuch neu).
- **FR-13:** `--dry-run` führt nur `decomposer` und S1 aus und gibt Tasks, Tokenverbrauch und die
  geschätzte Rollenverteilung aus, ohne Code zu schreiben.
- **FR-14:** `sdd pipeline report RUN_ID` zeigt pro Rolle Aufrufe, Tokens (in/out/reasoning),
  Dauer, Fehlversuche und Supervisor-Eingriffe sowie den Anteil der Claude-Tokens am Gesamtverbrauch.
- **FR-15:** **Entscheidungsquelle.** `llm.roles.supervisor.mode` ist `inline` (Default) oder
  `session`. Vor jeder Entscheidung schreibt der Mediator `pending-decision.json` mit Punkt, Fakten
  (Gate-Ergebnisse, Diffs, Fehlerausgaben, Tokenstand) und zulässigen Commands.
  - `inline`: Die Supervisor-Rolle antwortet über ihren Provider; der Run läuft weiter.
  - `session`: Der Run speichert `state.json`, setzt den Status `awaiting_supervisor` und endet mit
    Exit-Code 3. `sdd pipeline decide RUN_ID --json '<command>'` validiert das Command,
    protokolliert es und setzt den Run fort. `sdd pipeline status RUN_ID` zeigt die offene Anfrage.
- **FR-16:** Ein neuer Skill `/sdd-supervise SPEC-XXXX` startet den Run mit
  `supervisor.mode: session` und führt Claude Code durch die Schleife „Run fortsetzen → Anfrage
  lesen → entscheiden → `sdd pipeline decide`“. Der Skill legt Claudes Rolle ausdrücklich fest:
  - keine Edits an Code, Tests, Specs oder Contracts;
  - Entscheidungen nur auf Basis der Fakten aus der Anfrage, bei Bedarf ergänzt um lesenden Zugriff
    auf das Repo;
  - jede Entscheidung mit Begründung und Beleg;
  - dem Nutzer vorgelegt werden `halt` sowie jede S3-Abnahme mit `teilweise` oder `fehlt`.

  Für headless Läufe (CI, Benchmark) bleibt `inline` mit `claude-cli` der Default.

## 5. Nicht-funktionale Anforderungen

| Kategorie       | Anforderung                                                                      |
|-----------------|----------------------------------------------------------------------------------|
| Nachvollziehbarkeit | Jeder Rollenaufruf ist aus `events.jsonl` mit Prompt-Hash, Rollenversion, Modell und Usage rekonstruierbar. |
| Robustheit      | Ein nicht erreichbarer Modellserver führt zu `outcome: error` und S2, nicht zum Abbruch des Runs. Nach jedem Übergang ist `state.json` konsistent (atomar geschrieben). |
| Sicherheit      | Die PathPolicy gilt für alle Rollen und Provider (FR-07). API-Keys erscheinen nicht in Logs, `run.json` oder `state.json`. |
| Keyfreiheit     | Default-Supervisor ist `inline` mit `claude-cli`; kein Default verlangt `ANTHROPIC_API_KEY`. |
| Performance     | Der Overhead von Gates, Policy und Protokoll liegt pro Task unter 5 s, Testlaufzeit nicht eingerechnet. |

## 6. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: Rollenbasierte Pipeline

  Scenario: Decompose über ein Thinking-Modell
    Given llm.roles.decomposer zeigt auf ein openai-compat-Modell mit thinking: true
    When ich "sdd pipeline run SPEC-0900 --dry-run" ausführe
    Then enthält .sdd/tasks/SPEC-0900.json Tasks mit fr_ids
    And token_usage enthält einen Datensatz mit role=decomposer
    And es wurde kein claude-Prozess für die Zerlegung gestartet

  Scenario: Überarbeitung vor der Freigabe
    Given der decomposer liefert Tasks, die FR-03 nicht abdecken
    When der Rollen-Check fr_coverage fehlschlägt
    Then ruft die Pipeline den decomposer erneut mit der Check-Meldung auf
    And fragt S1 erst an, wenn alle Rollen-Checks grün sind

  Scenario: Supervisor schreibt keinen Code
    Given ein Task scheitert dreimal am Review
    When der supervisor mit "reassign(implementer, qwen3.8-27b)" antwortet
    Then bearbeitet das Modell qwen3.8-27b den Task in der Rolle implementer
    And decisions.jsonl enthält die Entscheidung mit Begründung
    And kein Datei-Schreibvorgang des Runs trägt role=supervisor

  Scenario: Supervisor im Dialog
    Given llm.roles.supervisor.mode ist session
    When der Run S1 erreicht
    Then existiert pending-decision.json und der Exit-Code ist 3
    When ich "sdd pipeline decide <run> --json '{\"command\": \"approve\"}'" ausführe
    Then läuft der Run ab dem gespeicherten Zustand weiter

  Scenario: Rückwärtskompatibilität
    Given config.yaml enthält keinen Block llm.roles
    When ich "sdd decompose SPEC-0900" ausführe
    Then wird der Provider aus llm.completion verwendet
```

## 7. Edge Cases & Fehlerfälle

- Das Thinking-Modell schöpft `max_output_tokens` im Reasoning aus und liefert leeren Content
  (`finish_reason=length`, bekannt vom MLX-Server): `outcome: invalid_output`, einmalige
  Wiederholung mit ×1,5, danach S2.
- Server ignoriert `enable_thinking` (MLX): Die Rollenkonfiguration erlaubt einen alternativen
  Modellnamen (z. B. `:no-think`); `sdd config test-llm --role <rolle>` meldet, ob Reasoning-Tokens
  zurückkommen.
- Der decomposer erzeugt einen Test-Task für einen Contract, der nicht existiert: Der Rollen-Check
  `deps_resolvable` schlägt fehl.
- `test_author` schreibt einen Test, der schon ohne Implementierung grün ist: Das RED-Gate schlägt
  fehl, und der Test wird verworfen.
- `implementer` ändert eine Datei außerhalb der erlaubten Pfade: Die PathPolicy lehnt ab,
  `gate_failed`.
- Abbruch während `session` wartet: `state.json` und `pending-decision.json` bleiben erhalten;
  `sdd pipeline decide` funktioniert auch in einer neuen Shell.
- `sdd pipeline decide` für einen Run ohne offene Anfrage: Exit 2 mit Hinweis.

## 8. Contracts (was wird garantiert)

| Contract-ID | Typ      | Was wird garantiert?                                                  |
|-------------|----------|-----------------------------------------------------------------------|
| CON-0199    | data     | `role-definition.schema.json`: Frontmatter einer Rollendatei          |
| CON-0200    | data     | Ausgabeschemata je Rolle (decomposer, test_author, implementer, reviewer) |
| CON-0201    | data     | `supervisor-decision.schema.json`: Commands für S1–S3                 |
| CON-0202    | data     | Run-Verzeichnis: `run.json`, `state.json`, `events.jsonl`, `decisions.jsonl`, `pending-decision.json` |
| CON-0204    | behavior | PathPolicy: Regeln je Rolle, Task und Pfad                            |
| CON-0205    | behavior | Pipeline-Ablauf, Entscheidungsquelle (`inline`/`session`), `--resume` |
| CON-0203    | data     | Erweiterung von CON-0096: `fr_ids`, `allowed_paths`                   |

## 9. Tests (wie wird verifiziert)

| Test-ID  | Level       | Was prüft der Test?                                                   |
|----------|-------------|-----------------------------------------------------------------------|
| TST-XXXX | unit        | Provider-Auflösung je Rolle inkl. `legacy_component`-Fallback (FR-04) |
| TST-XXXX | unit        | `RoleRunner`: Schema-Validierung, `invalid_output`, Längen-Retry, Usage-Übergabe |
| TST-XXXX | unit        | PathPolicy: jede Regel mit Positiv- und Negativfall                   |
| TST-XXXX | integration | Pipeline mit Fake-Providern: S1/S2/S3, RED-Gate, `session` + `decide`, `--resume` |
| TST-XXXX | acceptance  | Gherkin-Szenarien aus Abschnitt 6                                     |

## 10. Offene Fragen

- [x] Claude Code im Dialog als Supervisor → ja (FR-15, FR-16; entschieden 2026-09-25).
- [x] `task-loop` → wird von `pipeline run` abgelöst; geregelt in SPEC-0058 (entschieden 2026-09-25).
- [x] Überschneidende Pfade → SPEC-0058 (entschieden 2026-09-25).
- [x] Warnung bei gleichem Modell für Reviewer und Implementierer → ja (FR-04; entschieden 2026-09-25).
- [x] Usage-Erfassung der Provider → eigene SPEC-0060 (entschieden 2026-09-25).
- [ ] SPEC-0045 (`Task.executor`, Eskalation im `loop_controller`) liegt in PR #143 und muss vor
      der Umsetzung gemergt sein.

## 11. Änderungshistorie

| Datum      | Version | Autor         | Änderung            |
|------------|---------|---------------|---------------------|
| 2026-09-25 | 0.1.0   | Boris, Claude | Initiale Erstellung |
| 2026-09-25 | 0.2.0   | Boris, Claude | Supervisor im Dialog (`session`, `/sdd-supervise`) verbindlich; RED-Gate sprachneutral über JUnit |
| 2026-09-25 | 0.3.0   | Boris, Claude | `pipeline run` löst `task-loop` ohne Alias ab |
| 2026-09-25 | 0.4.0   | Boris, Claude | Warnung bei gleichem Modell für Reviewer und Implementierer |
| 2026-09-25 | 0.5.0   | Boris, Claude | Review: Patterns Template Method/Strategy/Mediator/Command; `supervisor.mode` + fortsetzbarer Zustandsautomat statt `provider: session` (LSP); PathPolicy (DIP); Grenze Rollen-Checks ↔ Gates; `legacy_component` in Rollendatei (OCP); Warnung bei wirkungslosen Parametern (ISP); Usage-Erfassung → SPEC-0060, `task-loop`-Ablösung → SPEC-0058; Abgrenzung zu SPEC-0004/0005/0007/0008/0011; FRs neu nummeriert |
