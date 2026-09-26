---
id: CON-0219
title: "Checks, Eval-Ablauf, Holdout-Sicht, capture und Rolle judge"
type: behavior
format: gherkin
spec: SPEC-0055
version: 0.1.0
status: approved
artifact: ".sdd/contracts/behavior/checks-eval-ablauf-holdout-sicht-capture-und-rolle-judge.feature"
tests: ["TST-0248"]
---

# Contract: Checks, Eval-Ablauf, Holdout-Sicht, capture und Rolle judge

> **Spec:** SPEC-0055 · **Typ:** Verhalten (Gherkin) · **Status:** approved

## Zweck

Legt das Verhalten von Check-Registry, `sdd role eval`, der Holdout-Sicht, `sdd role case new|capture|confirm` und der Rolle `judge` fest (SPEC-0055 FR-01 bis FR-06, FR-09, FR-11, FR-12).

## Garantien

Die Szenarien im Artifact (`.sdd/contracts/behavior/checks-eval-ablauf-holdout-sicht-capture-und-rolle-judge.feature`) sind **ausführbare Spezifikation**. Jedes Szenario MUSS durch einen automatisierten Test (pytest) abgedeckt sein; Rollen und Judge laufen gegen den Fake-LLM-Server.

## Invarianten

- **INV-01:** Die Registry `pipeline/checks.py` deklariert je Check `contexts` (`gate`, `eval`), benötigte Fall-Bestandteile und ein Parameterschema. Pipeline-Gates (SPEC-0053) nutzen nur Checks mit Kontext `gate`; eine Rolle mit Check ohne `gate` in ihren `checks` ist ungültig (`sdd validate`). Die bisherigen sechs Checks verhalten sich im Gate unverändert.
- **INV-02:** Ein Check liefert `pass`, `fail` oder `n/a` mit Score 0–1 und Details. Ausführungsbasierte Checks führen `test_command` mit Zeitlimit (`timeout_seconds`, Default 120) im Arbeitsverzeichnis aus; Zeitüberschreitung ist `fail` mit Grund. `mutation_kill_rate` wendet jeden Patch aus `mutants/` einzeln auf eine frische Kopie an; Score = getötete / alle Mutanten.
- **INV-03:** `sdd role eval` führt je Fall und Lauf den festen Ablauf aus: Arbeitsverzeichnis mit Kopie von `input/`, Nonce, Rolle ausführen, Ausgabe anwenden, Checks, Rubrik, Usage, Aufräumen. Das Projektverzeichnis ist danach byte-gleich. Exit 0, wenn der Lauf vollständig war; 2 bei ungültigen Fällen oder Profilen.
- **INV-04:** Ohne `--include-holdout` zeigen CLI-Ausgabe, JSON-Report und `compare` von Holdout-Fällen nur Anzahl und Aggregate. Alle Scanner von `.sdd/holdout/` für HOL-Szenarien ignorieren `.sdd/holdout/roles/`. Dieser Unterbaum ist ein eigener Namensraum: Die HOL-Regeln aus CON-0009 (ID-Format, Pflichtfelder, Klartext-Body, Anlage nur über `sdd new holdout`) und die Leseregel aus CON-0010 INV-01 gelten dort nicht; Rollen-Fälle entstehen über `sdd role case new|capture`.
- **INV-05:** Usage je Rollenaufruf landet in `token_usage` mit Kontext `origin: role-eval`, `role`, `case_id` und `eval_id`.
- **INV-06:** `sdd role case capture RUN ID` liest über `pipeline.store`/`monitor`. Eine Task-ID mit gescheitertem Rollenaufruf ergibt einen Fall der Rolle dieses Aufrufs mit den gescheiterten Checks; eine Request-ID einer Entscheidung ergibt einen `SUP-`-Fall mit `decision_matches`. Der Fall ist `draft: true`; unbekannte Run- oder Element-IDs ergeben Exit 2.
- **INV-07:** Die Rolle `judge` (`.sdd/roles/judge.md`, Belegung `llm.roles.judge`, Default `claude-cli`) bekommt Rubrik und anonymisierte Ausgabe, nie Modellnamen, Profil oder Rollenversion. `sdd quality --judge` nutzt dieselbe Rolle statt der Komponente `evaluator`. Hat der Judge denselben Endpunkt wie das bewertete Profil, warnt `sdd role eval`.
- **INV-08:** Der Profil-Schlüssel `requests_per_minute` (CON-0212 additiv) begrenzt die Aufrufe je Endpunkt; `--concurrency` (Default 2) die gleichzeitigen Aufrufe.
- **INV-09:** Holdout-Fälle liest nur der Prozess `sdd role eval` (und `sdd validate` zur
  Schemaprüfung ohne Ausgabe von Inhalten). Ihre Eingaben gehen an die geprüfte Rolle, wie
  HOL-Szenarien an den Service unter Test; die Erwartungen (`expected/`, `hidden/`, `reference/`,
  `mutants/`) nur an die Checks. Der Judge bekommt nur die anonymisierte Ausgabe. Weder
  Implementierungs- noch Tuning-Skills lesen sie (CON-0064 G-01 gilt entsprechend).
