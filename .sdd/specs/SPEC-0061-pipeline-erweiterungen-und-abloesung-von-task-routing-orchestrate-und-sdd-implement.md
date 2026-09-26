---
id: SPEC-0061
title: "Pipeline-Fähigkeiten: Session-Arbeitsrollen, Routing nach Komplexität, Abschluss-Schritte"
type: feature           # feature | bug-fix
status: draft           # draft | review | approved | implemented | deprecated
owner: "Boris"
created: 2026-09-26
updated: 2026-09-26
version: 0.2.0
priority: medium
tags: [pipeline, refactoring, session, routing]
depends_on: [SPEC-0053, SPEC-0054, SPEC-0058]
contracts: [CON-0212, CON-0213, CON-0214]           # z.B. ["CON-0001"] – MUSS mindestens einen Eintrag enthalten
tests: [TST-0241, TST-0242, TST-0243]               # z.B. ["TST-0001"] – MUSS mindestens einen Eintrag enthalten
---

# Pipeline-Fähigkeiten: Session-Arbeitsrollen, Routing nach Komplexität, Abschluss-Schritte

> **Status:** draft · **Owner:** Boris · **Version:** 0.2.0

## 1. Kontext & Motivation

SPEC-0058 hat die toten Ausführungspfade entfernt. Die lebendigen (`task_routing/`, `sdd
orchestrate`, `/sdd-implement`) lassen sich erst ablösen, wenn `sdd pipeline` kann, was sie heute
leisten. Die Bestandsaufnahme beim Review (2026-09-26) ergab diese Lücken:

| Fähigkeit | heute | Pipeline (SPEC-0053) |
|-----------|-------|----------------------|
| Modellwahl nach Komplexität | `task_routing`: `low/medium/high` → lokales Modell oder Claude | nur manuell per `reassign` (nur Modellname) |
| Claude implementiert im Dialog | `/sdd-implement` | nur der Supervisor kennt `session` |
| Einzelner Task | `sdd task-exec` | – |
| Nicht-Code-Tasks | ohne Gate | durchlaufen RED/GREEN |
| Lint- und Architektur-Gates pro Task | – | nur Tests |
| Abschluss | `orchestrate`: PR, Holdout-Evaluation mit Retry, Auto-Merge nach Autonomie-Level | nur `finalize` ohne Container |
| `sdd config test-llm` | liest den abgelösten `llm_pool`, derzeit wirkungslos | – |

Diese Spec ergänzt die Fähigkeiten. Die Ablösung der alten Pfade ist SPEC-0062.

## 2. Zielsetzung

**Primärziel:** `sdd pipeline` deckt alle Arbeitsweisen der alten Pfade ab: Arbeit im Dialog, lokale
Modelle nach Komplexität, einzelne Tasks und den autonomen Durchlauf bis zum Merge.

**Erfolgskriterien (messbar):**
- [ ] Ein Run mit `test_author` und `implementer` im Modus `session` läuft über `sdd pipeline done`
      bis zum Abschluss; dieselben Gates gelten wie bei LLM-Rollen.
- [ ] Mit `by_complexity` bearbeitet ein Task `low` ein anderes Profil als ein Task `high`; die
      Usage-Zeilen nennen das jeweilige Modell.
- [ ] `sdd pipeline run --auto` erzeugt nach S3 einen PR und merged ihn, wenn das Autonomie-Level es
      erlaubt; ein fehlgeschlagenes Holdout erscheint als Fakt der S3-Anfrage.
- [ ] `sdd config test-llm` prüft jede Belegung aus `llm.roles` und `llm.profiles`.

**Nicht-Ziele (explizit):**
- Keine Ablösung alter Befehle, kein Entfernen von `task_routing/` oder `orchestrator.py`
  (SPEC-0062).
- Die Holdout-Evaluation selbst (`evaluator.py`) bleibt unverändert; Holdouts gelangen nie in den
  Kontext einer Rolle.

## 3. Architektur & Design Patterns

- **Strategy:** Eine Rolle hat eine Belegung: LLM-Profil, `session` oder je Komplexität eines davon
  (`by_complexity`). Die Pipeline fragt nur die Rolle; welche Strategie greift, entscheidet die
  Belegung.
- **Command:** Eine Arbeitsrolle im Modus `session` erzeugt einen persistierten Auftrag
  (`pending-work.json`). Bestätigt wird mit einem eigenen Befehl (`sdd pipeline done`), nicht mit
  `decide` (ISP-Befund): Supervisor-Entscheidungen und Arbeitsergebnisse haben verschiedene Inhalte.
- **Chain of Responsibility:** Die Abschluss-Schritte (`holdout`, `finalize`, `automerge`) sind eine
  Kette aus der Config (`pipeline.auto_steps`). Jeder Schritt reicht weiter, gibt Fakten zurück oder
  hält an; neue Schritte kommen ohne Änderung am Kern dazu (OCP-Befund).
- **Rollenvertrag (LSP-Befund):** Für jeden Modus gelten dieselben Nachbedingungen: Änderungen nur in
  den Pfaden der PathPolicy, danach dieselben Gates, dieselbe Zählung der Versuche und dieselbe
  Eskalation (S2).

## 4. Funktionale Anforderungen

- **FR-01:** **Session-Arbeitsrollen.** `llm.roles.<rolle>.mode: session` ist für `decomposer`,
  `test_author`, `implementer` und `reviewer` erlaubt. Statt eines LLM-Aufrufs schreibt die Pipeline
  einen Auftrag nach `pending-work.json` (Rolle, Task, erlaubte Pfade, Kontextquellen als Verweise,
  Rückmeldungen aus früheren Versuchen), setzt den Status `awaiting_session` und endet mit Exit 3.
  `sdd pipeline status` zeigt den Auftrag.
- **FR-02:** **Bestätigung.** `sdd pipeline done RUN_ID [--json AUSGABE]` schließt den offenen
  Auftrag ab. Für `test_author` und `implementer` gelten die geänderten Dateien als Ergebnis; für
  `decomposer` und `reviewer` ist `--json` Pflicht und wird gegen das Ausgabeschema der Rolle
  (CON-0200) geprüft. Danach setzt der Run fort (Gates, nächste Rolle). Ohne offenen Auftrag oder
  mit ungültiger Ausgabe: Exit 2, der Auftrag bleibt offen.
- **FR-03:** **Rollenvertrag.** Nach `done` prüft die Pipeline jede seit dem Auftrag geänderte Datei
  mit der PathPolicy. Ein Verstoß wird als `write_rejected` protokolliert, der Versuch zählt als
  `gate_failed`, und der nächste Auftrag nennt die Datei zum Zurücksetzen (die Pipeline stellt
  Dateien einer Session nicht selbst zurück). Gates, Versuchszählung und S2 sind dieselben wie bei
  LLM-Rollen.
- **FR-04:** **Profile und Routing nach Komplexität.** `llm.profiles.<name>` beschreibt eine
  Modellbelegung (`provider`, `model`, `base_url`, `api_key`, Parameter wie in `llm.roles`).
  `llm.roles.<rolle>` darf `profile: <name>` nennen. `llm.roles.<rolle>.by_complexity` ordnet
  `low`, `medium` und `high` je ein Profil oder `session` zu; fehlt eine Stufe, gilt die Belegung
  der Rolle. Die Komplexität kommt aus der Zerlegung. Ein `reassign` des Supervisors hat Vorrang.
- **FR-05:** **Einzelner Task.** `sdd pipeline run SPEC --task ID` bearbeitet genau diesen Task der
  vorhandenen Zerlegung (`.sdd/tasks/SPEC.json`) in einem neuen Run: keine Zerlegung, kein S1, kein
  S3, kein Abschluss. Existiert die Zerlegung oder der Task nicht: Exit 2.
- **FR-06:** **Task-Typen.** `code`: test_author → RED → implementer → GREEN → reviewer. `test`:
  test_author → der Test läuft (kein RED-Zwang) → reviewer. `config` und `doc`: implementer →
  Testsuite ohne neue Fehler → reviewer.
- **FR-07:** **Gates pro Task.** Nach dem Implementer laufen die Gates aus `pipeline.task_gates`
  (Default `[tests, architecture]`, möglich außerdem `lint`). `architecture` wertet
  `.sdd/architecture.yaml` aus (neue Verstöße außerhalb der Baseline blockieren), `lint` die Sonde
  `pipeline.lint_probe` (Default `lint`) auf den geänderten Dateien (Befunde der Stufe `error`
  blockieren). Ein Gate ohne Konfiguration im Projekt ist `n/a` und blockiert nicht.
- **FR-08:** **Abschluss-Schritte.** `sdd pipeline run --auto` führt die Kette aus
  `pipeline.auto_steps` aus (Default `[holdout, finalize, automerge]`); ohne `--auto` gilt wie bisher
  nur `finalize`.
  - `holdout` läuft vor S3: `sdd holdout run` gegen `evaluator.base_url` (bzw. `--base-url`); das
    Ergebnis (bestandene/fehlgeschlagene Szenarien, Quote) wird Fakt der S3-Anfrage. Ohne Base-URL
    ist der Schritt `n/a` und wird gemeldet.
  - `finalize` erzeugt den PR (`SpecFinalizer`, Build aus `orchestrator.build_command`).
  - `automerge` labelt bzw. merged den PR, wenn das Autonomie-Level es erlaubt
    (`orchestrator.auto_merge`, `auto_merge_strategy`), und schreibt das Ergebnis in die
    Autonomie-Statistik.
- **FR-09:** **Wiedereröffnen nach S3.** S3 erlaubt zusätzlich `reopen` mit `task_ids` und `hint`:
  Die Tasks gehen zurück auf `red`, der Hinweis wird Kontextquelle `history`, der Run arbeitet sie
  erneut ab und fragt S3 erneut an. Die Zahl der Wiedereröffnungen begrenzt
  `pipeline.max_reopen` (Default 2); danach hält der Run an.
- **FR-10:** **`sdd config test-llm`.** Der Befehl prüft jede Belegung aus `llm.roles` und
  `llm.profiles` (`--role`, `--profile` schränken ein) mit einem kurzen Aufruf und meldet Erreichbarkeit,
  Dauer und ob Reasoning-Tokens gemeldet werden. `session`-Belegungen werden übersprungen.
  Mehrfach genutzte Endpunkte werden einmal geprüft.

## 5. Nicht-funktionale Anforderungen

| Kategorie   | Anforderung |
|-------------|-------------|
| Keyfreiheit | Keine neue Belegung verlangt `ANTHROPIC_API_KEY`; Default bleibt `claude-cli`. |
| Fortsetzbarkeit | `awaiting_session` überlebt Abbruch und neue Shell; `--resume` setzt am Auftrag fort. |
| Protokoll | Session-Aufträge und Abschluss-Schritte erscheinen in `events.jsonl` und im Monitor. |

## 6. Akzeptanzkriterien (Gherkin)

```gherkin
Feature: Pipeline-Fähigkeiten

  Scenario: Implementer im Dialog
    Given llm.roles.implementer.mode ist session
    When der Run den Implementer für T01 erreicht
    Then existiert pending-work.json mit Rolle implementer und den erlaubten Pfaden, Exit 3
    When die Session die Datei schreibt und "sdd pipeline done <run>" ausführt
    Then wertet die Pipeline das GREEN-Gate aus und setzt mit dem Reviewer fort

  Scenario: Routing nach Komplexität
    Given by_complexity ordnet low dem Profil lokal und high dem Profil claude zu
    When ein Task low und ein Task high bearbeitet werden
    Then nutzt der Implementer für den ersten Task lokal und für den zweiten claude

  Scenario: Holdout als Fakt der Abnahme
    Given pipeline.auto_steps enthält holdout und evaluator.base_url ist gesetzt
    When der Run nach allen Tasks S3 anfragt
    Then enthält die S3-Anfrage das Holdout-Ergebnis
    And der Supervisor kann mit reopen Tasks erneut bearbeiten lassen
```

## 7. Edge Cases & Fehlerfälle

- Die Session schreibt außerhalb der erlaubten Pfade: `write_rejected`, Versuch `gate_failed`, der
  nächste Auftrag nennt die Datei.
- `done` ohne Änderungen durch `implementer`: das GREEN-Gate entscheidet (meist `gate_failed`).
- `by_complexity` nennt ein unbekanntes Profil: `sdd config validate` meldet einen Fehler, der Run
  startet nicht (Exit 2).
- `--task` zusammen mit `--auto` oder `--resume`: Exit 2 mit Hinweis.
- Kein Git-Repository: `finalize` setzt nur den Status (wie bisher), `automerge` ist `n/a`.

## 8. Contracts (was wird garantiert)

| Contract-ID | Typ      | Was wird garantiert? |
|-------------|----------|----------------------|
| CON-0212    | data     | `llm.profiles`, `by_complexity`, Rollenmodus, `pipeline.task_gates`/`auto_steps`, Auftrag `pending-work.json`, Command `reopen` |
| CON-0213    | behavior | Session-Arbeitsrollen, `done`, Rollenvertrag, Task-Typen, Gates pro Task, `--task`, Routing |
| CON-0214    | behavior | Abschluss-Kette (`holdout`, `finalize`, `automerge`), `reopen`, `config test-llm` |

## 9. Tests (wie wird verifiziert)

| Test-ID  | Level       | Was prüft der Test? |
|----------|-------------|---------------------|
| TST-0241 | unit        | Schemas, Auflösung von Profilen und `by_complexity` |
| TST-0242 | acceptance  | Session-Rollen, Task-Typen, Gates, `--task` gegen den Fake-LLM-Server |
| TST-0243 | acceptance  | Abschluss-Kette mit Fake-Finalize/Holdout, `reopen`, `test-llm` |

## 10. Offene Fragen

- [x] Schnitt: Fähigkeiten hier, Ablösung in SPEC-0062 (entschieden 2026-09-26).
- [x] Holdout bei Fehlschlag: Fakt der S3-Anfrage, der Supervisor entscheidet (`reopen`), kein
      zweiter Retry-Automat (entschieden 2026-09-26).
- [x] Bestätigung von Session-Aufträgen: eigener Befehl `sdd pipeline done` (ISP-Befund).
- [x] Belegung von `/sdd-implement`: test_author, implementer und supervisor im Modus `session`
      (entschieden 2026-09-26, umgesetzt in SPEC-0062).

## 11. Änderungshistorie

| Datum      | Version | Autor         | Änderung |
|------------|---------|---------------|----------|
| 2026-09-26 | 0.1.0   | Boris, Claude | Aus SPEC-0058 0.1.0 abgespalten |
| 2026-09-26 | 0.2.0   | Boris, Claude | Review: nur Pipeline-Fähigkeiten, Ablösung in SPEC-0062; Rollenvertrag, Profile, Task-Typen, Abschluss-Kette, `reopen` |
