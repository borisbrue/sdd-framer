---
id: SPEC-0004
title: "Dark Factory Pattern Integration"
status: implemented
owner: "Boris"
created: 2026-05-11
updated: 2026-05-12
version: 0.8.0
priority: high
tags: ["autonomy", "dark-factory", "orchestration", "holdout", "evaluator"]
depends_on: ["SPEC-0001", "SPEC-0002", "SPEC-0003"]
contracts: ["CON-0009", "CON-0010", "CON-0011", "CON-0012", "CON-0016"]
tests: ["TST-0010", "TST-0010b", "TST-0011", "TST-0012", "TST-0015"]
adrs: []
---

# Dark Factory Pattern Integration

> **Status:** implemented · **Owner:** Boris · **Version:** 0.8.0

## 1. Kontext & Motivation

Das SDD-System liefert bisher die **Inputs-Schicht** des Dark Factory Patterns
(Specs, Contracts, Tests), aber keine Ausführungs-Pipeline. Der Artikel
[„The Dark Factory Pattern"](https://hackernoon.com/the-dark-factory-pattern-moving-from-ai-assisted-to-fully-autonomous-coding)
beschreibt einen vollständig autonomen Entwicklungs-Kreislauf, in dem Menschen
nur noch Specs schreiben und das System selbst implementiert, validiert und mergt.

Ziel dieser Spec ist es, sdd-framer schrittweise von Level 2 (AI schreibt Code,
Mensch reviewt) zu Level 4 (Spec rein → getesteter Code merged) zu entwickeln.

## 2. Zielsetzung

**Primärziel:**
sdd-framer wird zur vollständigen Orchestrierungsebene des Dark Factory Patterns –
Specs triggern einen autonomen Pipeline-Lauf, der Code generiert, validiert und
bei Bestehen der Quality Gates automatisch mergt.

**Erfolgskriterien (messbar):**
- [ ] Holdout-Szenarien sind vom Code-Generierungs-Agenten strukturell isoliert
- [ ] Ein Evaluator bewertet jedes Szenario 3× mit 2/3 Pass-Threshold
- [ ] Gesamt-Pass-Rate ≥ 90 % triggert Auto-Merge
- [ ] Menschliches Review reduziert sich auf den Satisfaction-Report (≤ 5 min statt 2 h)
- [ ] Autonomy-Level (1–4) pro Projekt trackbar und sichtbar in der Web-UI

**Nicht-Ziele (explizit):**
- Eigene CI/CD-Pipeline ersetzen – bestehende Pipelines bleiben unverändert
- Ephemeral Environments selbst bauen (Cloud-Provider-spezifisch, out of scope)
- Digital Twins / Mock-Server (separates Feature)

## 3. Fehlende Bausteine gegenüber dem Dark Factory Pattern

### 3.1 Holdout Scenarios — P0 🔴

Der kritischste fehlende Baustein. Im Dark Factory Pattern leben Akzeptanz-Tests
in **isolierten Verzeichnissen**, die dem Code-generierenden Agenten niemals
zugänglich sind (Train/Test-Trennung wie im ML).

**Aktueller Zustand:** Unsere `TST`-Dokumente sind für alle Agenten sichtbar.
Kein strukturelles Isolation-Konzept vorhanden.

**Dateiformat:** Jede HOL-Datei ist eine Markdown-Datei mit YAML-Frontmatter.
Das Szenario selbst wird im **Gherkin-Format** (Given/When/Then) im Body verfasst —
strukturiert genug, damit der Evaluator daraus HTTP-Calls ableiten kann, aber
lesbar genug für menschliche Autoren. Freier Fließtext ist nicht erlaubt.

```yaml
# .sdd/holdout/HOL-0001-login-success.md
---
id: HOL-0001
title: "Erfolgreicher Login"
contracts: ["CON-0001"]   # welche Contracts dieses Szenario prüft
status: active
---

Given ein registrierter Nutzer mit E-Mail "test@example.com" und Passwort "secret"
When POST /api/auth/login mit {"email":"test@example.com","password":"secret"}
Then HTTP 200 und response.token ist ein nicht-leerer String
```

**Pflichtfelder im Frontmatter:** `id`, `title`, `contracts` (mindestens 1 Eintrag).
`sdd validate` prüft die Vollständigkeit dieser Felder; die `contracts`-Liste muss
auf bekannte CON-IDs verweisen.

**HOL-ID-Vergabe:** `sdd new holdout` ruft `next_id(cfg, "holdout")` auf, das
alle `.md`-Dateien in `.sdd/holdout/` per Verzeichnis-Scan durchsucht und die
höchste vorhandene Nummer um 1 erhöht (gleicher Mechanismus wie für SPEC, CON, TST).
Es gibt keine zentrale Registry-Datei. Auf parallelen Feature-Branches kann
dieselbe HOL-ID vergeben werden — ein Git-Merge-Konflikt ist dann unvermeidlich
und muss manuell aufgelöst werden (identisches Verhalten wie bei allen anderen
SDD-Artefakt-Typen). Kein automatischer Schutzmechanismus gegen Kollisionen ist vorgesehen.

**Technische Isolation:** Die Isolation wird auf **Code-Ebene in `orchestrator.py`**
erzwungen, nicht durch Dateisystem-Permissions oder Git-Submodule. Der Orchestrator
baut den Prompt für Claude Code CLI ausschließlich aus diesen Quellen:
- Spec-Datei(en) aus `specs/`
- `AGENTS.md`
- Contracts aus `contracts/`

`.sdd/holdout/` wird beim Prompt-Aufbau explizit ausgeschlossen (Allowlist-Prinzip,
nicht Blocklist). Ein Entwickler, der `claude` direkt aufruft, unterliegt dieser
Einschränkung nicht — das ist bewusst akzeptiert, da der autonome Pfad ausschließlich
über `sdd orchestrate` läuft. Der Unit-Test TST-0010b verifiziert maschinell, dass
kein Holdout-Inhalt im erzeugten Prompt erscheint (siehe Acceptance Criteria US-01).

**Benötigt:**
- Neues Verzeichnis `.sdd/holdout/` für HOL-Szenarien im Gherkin-Format
- Holdout-Szenarien sind nicht Teil von `sdd validate` für den Code-Agenten
- Verknüpfung zu Contracts via `contracts`-Feld im Frontmatter
- Web-UI zum Erfassen und Verwalten von Holdout-Szenarien
- Neuer SDD-Artefakttyp `HOL-XXXX`

### 3.2 Evaluator — P0 🔴

Ein isolierter LLM-basierter Richter, der Holdout-Szenarien gegen eine laufende
Instanz auswertet.

**Aktueller Zustand:** KI wird nur zur Spec-Erstellung genutzt (Claude/Copilot),
nicht zur automatisierten Code-Evaluation.

**LLM-Modell:** Der Evaluator verwendet standardmäßig `claude-sonnet-4-6` via
Claude Code CLI (`claude --print --output-format json`). Das Modell ist
konfigurierbar in `.sdd/config.yaml` unter `evaluator.model` (CON-0013). Begründung:
Sonnet bietet den besten Kosten-Qualitäts-Tradeoff für automatisierte
Pass/Fail-Entscheidungen; kein separater `ANTHROPIC_API_KEY` nötig.

```yaml
# .sdd/config.yaml (Evaluator-Sektion)
evaluator:
  model: claude-sonnet-4-6          # überschreibbar
  base_url: http://localhost:8000
  timeout_per_scenario: 60          # Sekunden; Run gilt als failed wenn überschritten
  runs_per_scenario: 3
  pass_threshold: 2                 # von runs_per_scenario müssen passen
  cost_alert_usd: 1.00              # Default: $1,00 pro Evaluations-Lauf (alle Szenarien)
```

**Vorbedingung — laufende Instanz:** `sdd evaluate` übernimmt **nicht** das Starten
der Anwendung. Vor dem ersten Szenario führt `evaluator.py` einen HTTP-Health-Check
durch (`GET {base_url}/health` oder `GET {base_url}/`). Antwortet die Instanz nicht
mit HTTP 200 innerhalb von 5 s, bricht `sdd evaluate` mit Exit-Code 1 und einer
klaren Fehlermeldung ab: `"Instanz nicht erreichbar: {base_url}"`.

Der **GitHub-Actions-Workflow-Template** (`.sdd/templates/github-actions/sdd-orchestrate.yml`)
dokumentiert und übernimmt das Hochfahren der Instanz als separaten Job-Step vor dem
`sdd evaluate`-Aufruf. Das ist die einzige offizielle Dokumentation dieser Verantwortung.

**Kosten-Quelle:** `claude --output-format json` liefert den Outer-Wrapper
`{"type":"result","result":"...","total_cost_usd":0.001,...}`. `evaluator.py`
liest `total_cost_usd` aus diesem Wrapper aus — identisch zu `web/api/analyzer.py`
(Zeile `usage["cost_usd"] = outer["total_cost_usd"]`). Kein Token-Counting,
keine Preis-Tabelle nötig.

**Kosten-Alert und Hard-Stop:**
- Default-Limit: `evaluator.cost_alert_usd: 1.00` pro Evaluations-Lauf (alle Szenarien zusammen)
- Verhalten bei Überschreitung: **Hard-Stop** — der laufende Evaluations-Lauf wird abgebrochen,
  bereits abgeschlossene Szenario-Ergebnisse werden in `.sdd/evaluations.db` gespeichert,
  der PR erhält das Label `sdd:cost-limit`, ein GitHub Issue wird geöffnet
- Kosten werden nach jedem Szenario kumuliert geprüft (nicht erst am Ende)

**Evaluator-LLM-Output-Schema:** Der Prompt an das LLM fordert genau dieses JSON:

```json
{
  "passed": true,
  "reason": "Response enthielt ein nicht-leeres token-Feld.",
  "http_calls": [
    {
      "method": "POST",
      "url": "/api/auth/login",
      "body": {"email": "test@example.com", "password": "secret"},
      "response_status": 200,
      "response_body": {"token": "eyJ..."}
    }
  ]
}
```

Pflichtfelder: `passed` (bool), `reason` (string). `http_calls` ist optional aber
empfohlen — bei Fehlen wird `reason` als einzige Diagnose in den Report übernommen.
Fehlt `passed` oder ist das JSON nicht parsebar, gilt der Run als `failed`.

**Persistenz:** Evaluations-Ergebnisse werden in `.sdd/evaluations.db` (SQLite)
gespeichert. Diese Datei kann committed oder per `.gitignore` ausgeschlossen werden.
Schema: Tabelle `evaluations(id, pr_number, hol_id, run_index, passed, timestamp, cost_usd)`.
Auf dieser Tabelle bauen Auto-Merge-Logik (3.6) und Autonomy Level Tracking (3.5) auf.

**Benötigt:**
- Python-Modul `evaluator.py` (separater Prozess, kein Zugriff auf Sourcecode)
- Health-Check gegen `base_url` vor erstem Szenario; Abbruch mit klarer Fehlermeldung wenn nicht erreichbar
- LLM plant HTTP-Calls aus Gherkin-Szenario
- Führt Calls gegen konfigurierbaren `base_url` aus (lokal oder ephemeral)
- Bewertet Response mit LLM (Szenario erfüllt? ja/nein)
- 3 Runs pro Szenario, 2/3 müssen passen (konfigurierbar)
- Timeout pro Szenario-Run: 60 s (konfigurierbar via `evaluator.timeout_per_scenario`)
- Aggregierter Report: Pass-Rate, Details pro Szenario, kumulierte Kosten
- Persistenz in `.sdd/evaluations.db` (SQLite)
- Kosten-Monitoring: Hard-Stop wenn `cost_alert_usd` überschritten

### 3.3 AGENTS.md-Template — P1 🟡

Standardisiertes ~100-Zeilen Kontextdokument pro Repository, das dem
Code-generierenden Agenten den nötigen Kontext liefert.

**Aktueller Zustand:** Unsere Specs beschreiben *Was* (Requirements), aber nicht
den *Repository-Kontext* (Architektur, Verzeichnisstruktur, externe Abhängigkeiten)
in dem Format, das autonome Agenten erwarten.

**Pflicht- vs. optionale Sektionen:**

| Sektion                   | Typ       | `sdd validate`-Verhalten bei leer/fehlend |
|---------------------------|-----------|-------------------------------------------|
| Service-Zweck             | Pflicht   | Fehler                                    |
| Architektur               | Pflicht   | Fehler                                    |
| Build-Befehle             | Pflicht   | Fehler                                    |
| Verzeichnisstruktur       | Optional  | Warnung                                   |
| Externe Abhängigkeiten    | Optional  | Warnung                                   |
| Linting-Regeln            | Optional  | Warnung                                   |

„Leer" bedeutet: Sektion vorhanden, aber Body enthält nur den Platzhalter-Kommentar
aus dem Template (z. B. `<!-- TODO -->`). Fehlend bedeutet: Sektion-Heading nicht vorhanden.

**Benötigt:**
- `sdd new agents-md` CLI-Befehl generiert AGENTS.md-Skeleton
- Template mit allen 6 Sektionen (3 Pflicht, 3 Optional)
- AGENTS.md wird in `sdd validate` auf Vollständigkeit geprüft (Pflicht = Fehler, Optional = Warnung)
- Web-UI zeigt AGENTS.md-Status pro Projekt

### 3.4 Orchestrator — P1 🟡

Der Pipeline-Motor, der Spec-Commits in Code-PRs verwandelt.

**Aktueller Zustand:** Alles manuell. Keine Automatisierung von Spec → Code → PR.

**Code-generierender Agent:** Der Orchestrator ruft **Claude Code CLI** auf
(`claude --print` via Subprocess), identisch zur Analyzer-Implementierung in
`web/api/analyzer.py`. Der vollständige Spec-Inhalt plus AGENTS.md werden als
Prompt übergeben. `.sdd/holdout/` wird beim Prompt-Aufbau explizit ausgeschlossen
(Allowlist-Prinzip, siehe 3.1).

**Verhalten nach 3 fehlgeschlagenen Retries:**
1. PR bleibt offen, erhält Label `sdd:failed`
2. Ein GitHub Issue wird automatisch erstellt mit dem Titel
   `[SDD] Auto-Merge fehlgeschlagen: <PR-Titel>` und enthält den letzten
   Evaluator-Report als Body
3. Kein weiterer automatischer Retry — menschliches Eingreifen erforderlich
4. `sdd orchestrate --resume <pr-number>` startet den Zyklus manuell neu

**Retry-Prompt-Kontext:** Beim Retry erhält der Claude-Code-CLI-Aufruf den ursprünglichen
Prompt plus folgenden Anhang im Markdown-Format:

```
## Vorheriger Versuch fehlgeschlagen (Attempt {N})

Folgende Holdout-Szenarien sind nicht bestanden:

| HOL-ID  | Titel                  | Fehlschlag-Grund                          |
|---------|------------------------|-------------------------------------------|
| HOL-001 | Erfolgreicher Login    | HTTP 401 statt 200; response.token fehlt  |

### Details: HOL-001 (letzter Run)
HTTP-Calls ausgeführt:
POST /api/auth/login → 401 {"error":"invalid_credentials"}

Evaluator-Begründung: "Response enthielt keinen token-Wert."

Bitte korrigiere den Code so, dass alle obigen Szenarien bestehen.
```

Eingefügt werden: die HOL-IDs und Titel fehlgeschlagener Szenarien, die konkreten
HTTP-Calls und Response-Bodies des letzten Runs (aus `http_calls` im Evaluator-JSON),
sowie der `reason`-Text des LLM. Bestandene Szenarien werden nicht wiederholt.
Maximale Anhang-Länge: 8 000 Zeichen (Truncation mit Hinweis wenn überschritten).

**Verhalten von `--resume` und Token-Hard-Cap:**
`--resume` setzt den Retry-Zähler auf 0 zurück — dies ist **bewusst**, weil ein Mensch
den Misserfolg bewertet und entschieden hat, einen neuen Zyklus zu starten.
Jede `--resume`-Ausführung wird in `evaluations.db` als `resume_event` geloggt
(Tabelle: `resume_events(id, pr_number, triggered_by, timestamp)`).
Es gibt keinen Hard-Cap auf die Anzahl von `--resume`-Aufrufen, aber die Kosten
pro Lauf werden durch `evaluator.cost_alert_usd` begrenzt (Hard-Stop, siehe 3.2).
Der kumulative Token-Verbrauch über alle Zyklen ist über `evaluations.db` nachvollziehbar.

**Benötigt:**
- Python-Skript `orchestrator.py` (GitHub-Actions-triggered)
- Workflow: Spec-Datei empfangen → Claude Code CLI aufrufen → Build → PR erstellen →
  Evaluator laufen lassen → bei Erfolg merge/label, bei Fehler retry (max. 3×)
- Nach 3 Retries: Label `sdd:failed` + GitHub Issue als Benachrichtigung
- GitHub Actions Workflow-Template als SDD-Artefakt (inkl. Instanz-Start-Step)
- Retry-Logik mit kontextangereicherten Fehlermeldungen
- Token-Monitoring + Hard-Cap bei 3 Retries pro Zyklus

### 3.5 Autonomy Level Tracking — P1 🟡

Messbare Einordnung jedes Projekts/Services auf der Dark Factory Skala.

**Aktueller Zustand:** Projekte haben nur `status: active|planning|archived`.
Kein Konzept für Autonomie-Level.

**Level-Kriterien und Upgrade-Schwellwerte:**

| Level | Bezeichnung          | Pass-Rate (letzte N PRs) | Override-Rate | Min. PRs | Auto-Merge |
|-------|----------------------|--------------------------|---------------|----------|------------|
| 1     | Vollständig manuell  | —                        | —             | —        | nein       |
| 2     | AI-assisted          | —                        | ≤ 100 %       | 0        | nein       |
| 3     | AI-reviewed          | ≥ 70 %                   | ≤ 30 %        | 10       | nein       |
| 3.5   | AI-gated             | ≥ 85 %                   | ≤ 15 %        | 20       | optional   |
| 4     | Fully autonomous     | ≥ 90 %                   | ≤ 5 %         | 50       | ja         |

**Rolling Window:** N entspricht den **Min. PRs des Ziel-Levels**. Für einen
Level-4-Upgrade-Vorschlag werden also die letzten 50 PRs betrachtet; für Level 3
die letzten 10. Das Berechnungs-Window ist nicht von Min. PRs entkoppelt —
Window = Min. PRs des jeweiligen Levels.

**Level-Upgrade:** Wird vorgeschlagen (nicht automatisch ausgeführt), wenn alle
Schwellwerte des nächsten Levels über das zugehörige Window erfüllt sind.
Bestätigung via Web-UI oder `sdd set-level <level>`.

**Level-Downgrade und Auto-Merge-Block:**
- Fällt die Pass-Rate **unterhalb** den Schwellwert des aktuellen Levels (geprüft
  nach jedem neu abgeschlossenen PR), wird Auto-Merge **sofort blockiert** —
  das Label `sdd:approved` wird nicht mehr gesetzt.
- Sobald 5 aufeinanderfolgende PRs unter dem Schwellwert liegen, erscheint in der
  Web-UI ein **Downgrade-Vorschlag** auf das nächstniedrigere Level.
- Downgrade ist nie automatisch — der Nutzer bestätigt via Web-UI oder
  `sdd set-level <level>`.
- Nach bestätigtem Downgrade wird Auto-Merge entsprechend dem neuen Level wieder
  freigegeben oder bleibt gesperrt (Level 1/2 = kein Auto-Merge).

**Override-Rate:** Anteil der PRs, bei denen der Mensch nach Auto-Merge manuell
einen Revert oder Fix-Commit pushte (erkannt via `sdd mark-false-positive`).

**Benötigt:**
- Neues Feld `autonomy_level: 1|2|3|3.5|4` in Projekt-YAML
- Level-Kriterien und Rolling-Window wie oben dokumentiert und prüfbar
- Sichtbar in der Web-UI pro Projekt
- Level-Upgrade-Vorschlag wenn alle Schwellwerte erfüllt sind
- Level-Downgrade-Vorschlag nach 5 aufeinanderfolgenden PRs unter Schwellwert
- Auto-Merge-Block sofort bei Unterschreitung des aktuellen Schwellwerts

### 3.6 Auto-Merge-Logik — P2 🟢

Automatisches Mergen wenn Quality Gates bestanden sind.

**Aktueller Zustand:** Kein Auto-Merge-Konzept.

**Auslösemechanismus:** Standard ist **Label-basiert** — der Orchestrator setzt
`sdd:approved`, GitHub-Branch-Protection-Rules lösen den Merge via GitHub API aus.
Direkter Merge via GitHub API (ohne Label) ist opt-in via
`auto_merge_strategy: direct` in `.sdd/config.yaml`.

**GitHub-Bot-Voraussetzungen:** Das Setzen von `sdd:approved` und das Öffnen von
GitHub Issues erfordert einen dedizierten Bot-Account oder eine GitHub App mit
folgenden Permissions:

| Permission          | Scope           | Begründung                              |
|---------------------|-----------------|-----------------------------------------|
| `pull_requests`     | write           | Label setzen, PR kommentieren           |
| `issues`            | write           | Failure-Issue öffnen                    |
| `contents`          | write           | Branch mergen (bei `direct`-Strategie)  |

Empfohlen: **GitHub App** (feingranulare Permissions, kein persönliches Token).
Einrichtung und Token-Hinterlegung als `SDD_GITHUB_TOKEN` Secret sind in
CON-0013 (config.yaml-Schema) und dem GH-Actions-Workflow-Template zu dokumentieren.

**Branch-Protection-Voraussetzungen (Minimum):**
- 1 Status-Check muss bestehen (der SDD-Evaluator-Check)
- Keine required reviews für Level-4-Projekte (Ziel: manuelles Review eliminieren)
- `sdd:approved`-Label darf nur vom SDD-Bot / der GitHub App gesetzt werden

**Auto-Merge und Level-Mindest-Sample:**
`auto_merge: true` ist nur wirksam, wenn das Projekt genug Daten in `evaluations.db`
hat, entsprechend dem aktuellen `autonomy_level`:

| autonomy_level | Min. PRs für Auto-Merge |
|----------------|-------------------------|
| 1, 2           | Auto-Merge nicht erlaubt |
| 3              | 10                       |
| 3.5            | 20                       |
| 4              | 50                       |

Liegt die PR-Anzahl unter dem Level-Minimum, wird Auto-Merge **blockiert** und
eine Warnung ausgegeben: `"Auto-Merge deaktiviert: {N} PRs vorhanden, Minimum für
Level {L} ist {M}."` Das Minimum von 10 PRs aus den NFR ist der absolute Floor
für Level 3; höhere Level setzen höhere Minima.

**False-Positive-Rate:** Ein Merge-Ergebnis wird als False Positive markiert, wenn
der Mensch danach einen Revert oder direkten Fix-Commit pusht. Erfassung über:
- `sdd mark-false-positive <pr-number>` (CLI)
- Label `sdd:false-positive` am PR (GitHub UI)
- Beide Wege schreiben in `evaluations.db` → Tabelle `false_positives`

**Benötigt:**
- Metriken-Persistenz in `.sdd/evaluations.db`: Pass-Rate (letzte 20 PRs),
  False-Positive-Rate, Override-Rate
- Konfigurierbarer Auto-Merge-Schwellwert (Default: Pass-Rate ≥ 90 %)
- Auto-Merge nur wenn PR-Anzahl ≥ Level-Minimum (siehe Tabelle oben)
- Ein-Zeilen-Konfiguration in `.sdd/config.yaml`: `auto_merge: true/false`
- Dashboard in Web-UI mit Metriken-Verlauf

### 3.7 Linter-Instruktionen — P2 🟢

Linting-Regeln geben Handlungsanweisungen statt nur Fehlermeldungen.

**Aktueller Zustand:** `sdd validate` gibt Fehler aus, aber keine
handlungsorientierten Korrekturen im Stil von
*„Move shared type to model package"*.

**Benötigt:**
- Erweiterung der Issue-Klasse um `instruction`-Feld
- CLI gibt bei `--instruct` Flag maschinenlesbare Anweisungen aus (JSON)
- Agenten-freundliches Output-Format

### 3.8 Quality Maintenance Agents — P3 🟢

Wöchentliche Background-Jobs zur Drift-Erkennung.

**Code-Generierung in Cleanup-PRs:** Der Maintenance Agent delegiert an den
**Orchestrator** — er ruft `sdd orchestrate` mit der veralteten Spec als Input
auf, identisch zu einem regulären Spec-Commit-Trigger. Der Input-Prompt ist die
Spec-Datei selbst (keine generischen Update-Aufträge). Der Cleanup-PR durchläuft
denselben Evaluations-Kreislauf wie jeder andere PR.

**Benötigt:**
- Cron-Job-Konfiguration in `.sdd/config.yaml`
- Sweep: veraltete Specs (`updated` älter als `stale_after_weeks` Wochen;
  Default: 4, konfigurierbar via `.sdd/config.yaml` → `maintenance.stale_after_weeks`)
- Fehlende Contracts und Drift prüfen
- Öffnet automatisch Cleanup-PRs via `sdd orchestrate <spec-file>` (kein separater Code-Pfad)

## 4. User Stories

| ID    | Als ...    | möchte ich ...                               | um ...                                       |
|-------|-----------|----------------------------------------------|----------------------------------------------|
| US-01 | Entwickler | Holdout-Szenarien in Gherkin schreiben        | sicherzustellen dass der Agent sie nie sieht |
| US-02 | Entwickler | einen Evaluator-Report pro PR erhalten        | Code-Review auf 5 min zu reduzieren          |
| US-03 | Tech Lead  | den Autonomy-Level pro Projekt sehen          | den Dark-Factory-Reifegrad zu messen         |
| US-04 | Entwickler | AGENTS.md per CLI generieren                  | dem Agenten den nötigen Kontext zu geben     |
| US-05 | Tech Lead  | Auto-Merge per Konfiguration aktivieren       | den manuellen Merge-Schritt zu eliminieren   |

**Acceptance Criteria:**

**US-01:**
- `sdd new holdout` erstellt eine Datei in `.sdd/holdout/HOL-XXXX-<slug>.md` mit Gherkin-Template
- `sdd validate` schlägt fehl wenn `id`, `title` oder `contracts` fehlen
- `sdd validate` schlägt fehl wenn ein `contracts`-Eintrag auf keine bekannte CON-ID zeigt
- **TST-0010b** verifiziert maschinell: der von `orchestrator.py` erzeugte Prompt enthält
  keinen Dateiinhalt aus `.sdd/holdout/` — der Test liest den erzeugten Prompt-String
  direkt aus der `build_prompt()`-Funktion und prüft, dass keine HOL-Inhalte enthalten sind

**US-02:**
- `sdd evaluate` gibt einen Report auf stdout aus: Pass-Rate gesamt, Status pro HOL-ID
- Report enthält Kosten-Schätzung in USD
- Bei Timeout eines Szenarios (> `evaluator.timeout_per_scenario`) gilt der Run als `failed`
- Bei Überschreitung von `cost_alert_usd`: Hard-Stop, Label `sdd:cost-limit`, GitHub Issue
- Ergebnisse werden in `.sdd/evaluations.db` persistiert

**US-03:**
- `autonomy_level` ist ein Pflichtfeld in Projekt-YAML mit erlaubten Werten `1|2|3|3.5|4`
- Web-UI zeigt Level als Badge (z. B. „Level 3.5 — AI-gated")
- Web-UI zeigt Upgrade-Vorschlag wenn alle Schwellwerte aus Abschnitt 3.5 erfüllt sind

**US-04:**
- `sdd new agents-md` legt `AGENTS.md` im Projekt-Root an wenn sie noch nicht existiert
- `sdd validate` gibt Warnung aus wenn AGENTS.md fehlt oder Pflicht-Sektionen leer sind

**US-05:**
- `auto_merge: true` in `.sdd/config.yaml` aktiviert Auto-Merge
- Auto-Merge wird blockiert wenn PR-Anzahl < Level-Minimum (Warnung statt Silent-Fail)
- Bei aktiviertem Auto-Merge und bestandenen Quality Gates: Label `sdd:approved` wird gesetzt

## 5. Nicht-funktionale Anforderungen

| Kategorie          | Anforderung                                                                                          |
|--------------------|------------------------------------------------------------------------------------------------------|
| Isolation          | Holdout-Szenarien dürfen dem Code-Agenten strukturell nicht zugänglich sein (Allowlist in `orchestrator.py`, verifiziert durch TST-0010b) |
| Kosten             | Evaluator: Hard-Cap 3 Retries pro Zyklus; Hard-Stop bei `cost_alert_usd` (Default $1,00)            |
| Reproduzierbarkeit | 3 Runs pro Szenario, 2/3 Pass-Threshold (konfigurierbar)                                             |
| Kompatibilität     | Bestehende CI/CD-Pipelines bleiben unverändert                                                       |
| Konfiguration      | `.sdd/config.yaml`-Schema ist vollständig in CON-0013 spezifiziert und validiert                     |
| Timeout            | Max. 60 s pro Evaluator-Szenario-Run (konfigurierbar); bei Überschreitung: Run = failed              |
| Mindest-Sample     | Auto-Merge erst ab Level-spezifischem Minimum (Level 3: 10, Level 3.5: 20, Level 4: 50 PRs)         |
| Vorbedingung       | `sdd evaluate` prüft Health-Check gegen `base_url` vor erstem Szenario; Abbruch wenn nicht erreichbar |

## 6. Implementierungs-Reihenfolge

```
Phase A (P0): Holdout Scenarios + Evaluator  ✅ implementiert
  └─ CON-0009: Holdout-Verzeichnisstruktur-Isolation
  └─ CON-0010: Evaluator-Standalone-Prozess
  └─ TST-0010: Evaluator-Integrations-Test
  └─ TST-0010b: Prompt-Isolation-Unit-Test  ✅ implementiert
  └─ CLI: sdd new holdout | sdd evaluate
  └─ Modul: tool/sdd_cli/evaluator.py

Phase B (P1): AGENTS.md + Orchestrator + Autonomy Level  ✅ implementiert
  └─ CON-0011: AGENTS.md-Schema-Contract  ✅
  └─ CLI: sdd new agents-md  ✅
  └─ CON-0012: Orchestrator-Pipeline-Contract  ✅
  └─ TST-0012: Orchestrator-Integrations-Test  ✅
  └─ CLI: sdd orchestrate | sdd new github-workflow  ✅
  └─ Template: .sdd/templates/github-actions/sdd-orchestrate.yml  ✅
  └─ Autonomy Level Tracking  ✅ implementiert
      └─ Modul: tool/sdd_cli/autonomy.py (SQLite evaluations.db, Level-Berechnung)
      └─ CLI: sdd set-level | sdd level
      └─ projects.py: autonomy_level-Feld + save_project()

Phase C (P2–P3): Auto-Merge + Linter-Instruktionen + Maintenance Agents  ✅ implementiert
  └─ CON-0016: config.yaml-Schema-Contract  ✅
  └─ .sdd/config.yaml: evaluator-Sektion  ✅
  └─ Auto-Merge: sdd:approved Label, autonomy_level-Check, sdd:failed + GH Issue  ✅
  └─ orchestrate: --project, --resume, LABEL_APPROVED/LABEL_FAILED  ✅
  └─ sdd mark-false-positive: False-Positive-Tracking in evaluations.db  ✅
  └─ Linter-Instruktionen: instruction-Feld in Issue, sdd validate --instruct  ✅
  └─ Quality Maintenance Agents: sdd maintenance (stale, drift, --auto-pr)  ✅
      └─ Modul: tool/sdd_cli/maintenance.py
```

## 7. Offene Fragen

- [x] Soll `HOL-XXXX` ein eigener ID-Typ werden oder `TST` mit `holdout: true` Flag?
      → **HOL-XXXX** als eigener Typ (strukturelle Isolation, `.sdd/holdout/`)
- [x] Evaluator: eigener API-Service oder eingebettet in sdd-web-api?
      → **Eigenständiger Python-Prozess** (`sdd evaluate`, kein eigener Service)
- [x] Orchestrator: GitHub-Actions-only oder auch andere CI-Systeme (GitLab CI, etc.)?
      → **Lokaler Python-Prozess** (`sdd orchestrate`). CI-Systeme rufen ihn als thin wrapper auf.
        GitHub-Actions-Workflow ist ein SDD-Template-Artefakt, kein eigenes Modul.
- [x] Auto-Merge: direkt gegen GitHub API oder nur Label setzen?
      → **Label-basiert** (`sdd:approved`) als Standard; direkter GitHub-API-Merge opt-in
        via `auto_merge_strategy: direct`. Branch-Protection-Voraussetzung: 1 CI-Check
        (SDD-Evaluator), keine required reviews für Level-4-Projekte.
- [ ] Wie werden ephemeral Environments konfiguriert? (Cloud-agnostisch via env var?)
      **Vorbedingung bis zur Klärung:** `sdd evaluate` erwartet eine bereits laufende
      Instanz unter `evaluator.base_url` und prüft dies via Health-Check. Das Hochfahren
      der Instanz ist Verantwortung des Aufrufers und wird im GH-Actions-Workflow-Template
      dokumentiert.

## 8. Änderungshistorie

| Datum      | Version | Autor   | Änderung                                                                                   |
|------------|---------|---------|--------------------------------------------------------------------------------------------|
| 2026-05-11 | 0.1.0   | Boris   | Initiale Erstellung nach Artikel-Analyse                                                   |
| 2026-05-11 | 0.2.0   | Boris   | Phase A+B (teilweise) implementiert: HOL-Typ, evaluator.py, CON-0009/0010/0011, TST-0010, AGENTS.md |
| 2026-05-12 | 0.3.0   | Boris   | Orchestrator implementiert: CON-0012, TST-0012, orchestrator.py, sdd orchestrate, GH-Actions-Template |
| 2026-05-12 | 0.4.0   | Boris   | KI-Analyse-Lücken geschlossen: Gherkin-Format, Evaluator-Modell/-Persistenz, Level-Schwellwerte, Retry-Endzustand, False-Positive-Mechanismus, Acceptance Criteria, NFR-Timeouts |
| 2026-05-12 | 0.5.0   | Boris   | Isolation technisch spezifiziert (Allowlist + TST-0010b), Health-Check als Vorbedingung, Kosten-Hard-Stop, --resume-Semantik, Auto-Merge an Level-Minimum gekoppelt, CON-0013 für config.yaml-Schema, Maintenance-Agent-Delegation an Orchestrator |
| 2026-05-12 | 0.6.0   | Boris   | HOL-ID-Kollisionsverhalten dokumentiert, cost_usd-Quelle (total_cost_usd aus CLI-Wrapper), Evaluator-LLM-Output-Schema, Retry-Prompt-Format, Rolling-Window = Min. PRs, Downgrade-Kriterien, AGENTS.md Pflicht/Optional-Klassifizierung, GitHub-Bot-Permissions |
| 2026-05-12 | 0.7.0   | Boris   | TST-0010b implementiert (Prompt-Isolation-Unit-Test), autonomy.py (SQLite evaluations.db, Level-Berechnung, Upgrade-/Downgrade-Vorschläge), sdd set-level + sdd level CLI, projects.py autonomy_level-Feld, CON-0016 (config.yaml-Schema), .sdd/config.yaml evaluator-Sektion |
| 2026-05-12 | 0.8.0   | Boris   | Phase C vollständig: Auto-Merge (sdd:approved, sdd:failed, GH Issue), sdd mark-false-positive, orchestrate --project/--resume, Linter-Instruktionen (instruction-Feld + --instruct JSON), maintenance.py (sdd maintenance --auto-pr) |
