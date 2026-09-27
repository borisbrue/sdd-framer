---
id: CON-0224
title: "Bench-Report, Vergleich und config apply-roles"
type: behavior
format: gherkin
spec: SPEC-0056
version: 0.1.0
status: draft
artifact: ".sdd/contracts/behavior/bench-report-vergleich-und-config-apply-roles.feature"
tests: ["TST-0253"]
---

# Contract: Bench-Report, Vergleich und config apply-roles

> **Spec:** SPEC-0056 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Legt Kennzahlen, Pareto-Front, Signifikanzhinweis, `sdd bench report`, `sdd bench compare` und `sdd config apply-roles` fest (SPEC-0056 FR-07, FR-08, FR-11).

## Garantien

Die Szenarien im Artifact (`.sdd/contracts/behavior/bench-report-vergleich-und-config-apply-roles.feature`) sind **ausführbare Spezifikation**; Grundlage sind Fixture-Records.

## Invarianten

- **INV-01:** Kennzahlen je Belegung und `q_kind`: Mittel und Standardabweichung von `Q` (und bei `quality` von `Q_req`, `Q_arch`, `Q_code`) über Wiederholungen, Summen und Mittel von `T_in`, `T_out`, `T_reason`, `T_claude`, Effizienz `Q / (T / 1e5)` (mit `--exclude-reasoning` ohne `T_reason`), Tokens je erfülltem FR (`T / frs_met`, bei 0 erfüllten FRs „–“), Fehlversuche.
- **INV-02:** Die Pareto-Front über (Q ↑, T ↓) enthält genau die Belegungen, die von keiner anderen mit mindestens gleichem Q und höchstens gleichem T bei mindestens einer echten Verbesserung dominiert werden; sie wird getrennt für T mit Claude-Tokens und für T ohne Claude-Tokens bestimmt.
- **INV-03:** Zwei Belegungen gelten als „nicht unterscheidbar“, wenn der Unterschied ihrer mittleren Q kleiner ist als die gepoolte Standardabweichung beider.
- **INV-04:** Records mit verschiedenem `q_kind` erscheinen in getrennten Abschnitten; es gibt kein gemeinsames Ranking. Mit `--by role` erscheint je Rolle eine Rangliste der Profile (aus `roles` bzw. `sweep`).
- **INV-05:** `sdd bench report` schreibt `report.md` (und mit `--html` `report.html` mit Diagramm) in den Ergebnisordner und nichts sonst; geschätzte Tokens sind mit `*` markiert.
- **INV-06:** `sdd bench compare A B` zeigt je Belegung und `q_kind` das Delta von Q und T mit Signifikanzhinweis und warnt, wenn der gemeldete Modellname eines Profils in A und B verschieden ist. Exit 0.
- **INV-07:** `sdd config apply-roles --from ORDNER --assignment NAME` zeigt den `llm.roles`-Block der Belegung (Profil je Rolle, Variante als Parameter) als Diff gegen `config.yaml`; geschrieben wird nur mit `--yes` oder nach Bestätigung, Kommentare außerhalb von `llm.roles` bleiben erhalten. Unbekannte Belegung: Exit 2.
