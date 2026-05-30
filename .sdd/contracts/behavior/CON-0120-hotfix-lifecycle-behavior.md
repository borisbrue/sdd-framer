---
id: CON-0120
project: ""                # PRJ-XXXX
title: "Hotfix Lifecycle Behavior"
type: behavior
format: gherkin
spec: SPEC-0031
version: 0.1.0
status: approved
artifact: ".sdd/contracts/behavior/hotfix-lifecycle-behavior.feature"
tests: ["TST-0139"]
---

# Contract: Hotfix Lifecycle Behavior

> **Spec:** SPEC-0031 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Beschreibt das beobachtbare Verhalten der vier Hotfix-CLI-Kommandos (FR-01, FR-03,
FR-04, FR-05): `start`, `finalize`, `abort`, `list`. Legt fest welche Zustandsübergänge
erlaubt sind und welche Seiteneffekte (Commit, Record-Update, Audit-Log) eintreten.

## Garantien

Die im Artifact (`.sdd/contracts/behavior/hotfix-lifecycle-behavior.feature`) hinterlegten Szenarien sind **ausführbare Spezifikation**.
Jedes Szenario MUSS durch einen automatisierten Test (behave oder pytest-bdd) abgedeckt sein.

## Invarianten (über alle Szenarien hinweg)

- **INV-01:** `sdd hotfix start` erzeugt einen Record mit `status: open` ohne LLM-Aufruf und ohne Container-Start — der Befehl schließt in unter 3 Sekunden ab.
- **INV-02:** `sdd hotfix finalize HF-XXXX` ist nur für Records mit `status: open` gültig; bei `status: done` oder `status: aborted` bricht der Befehl mit Exit-Code 1 ab.
- **INV-03:** Nach erfolgreichem `sdd hotfix finalize` enthält der Record den Commit-Hash des erzeugten Commits und `status: done`; der Commit enthält ausschließlich die vor dem Aufruf gestagten Änderungen.
- **INV-04:** `sdd hotfix abort HF-XXXX` setzt `status: aborted` ohne Commit; staged Änderungen bleiben unverändert im Index.
- **INV-05:** `sdd hotfix list` zeigt alle Records mit `status: open` tabellarisch; abgeschlossene und abgebrochene Records erscheinen nicht (ohne explizites Flag).

## Begriffe

| Begriff        | Definition |
|----------------|------------|
| Hotfix-Record  | Minimales Markdown-Dokument in `.sdd/hotfixes/HF-XXXX.md` mit id, description, status, created, commit |
| finalize       | Committet staged Changes, trägt Commit-Hash ein, setzt status: done |
| abort          | Setzt status: aborted ohne Commit; kein Datenverlust im Git-Index |
| Audit-Log      | Eintrag in `sdd status`-Ausgabe unter eigenem Hotfix-Abschnitt (FR-06) |
