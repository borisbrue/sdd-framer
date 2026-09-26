---
scope: role-tuning
---
<!-- skill: sdd-role-tune | version: 0.1.0 | sdd-blueprint: true | updated: 2026-09-26 -->

# /sdd-role-tune – Rollendefinition gegen Golden Cases verbessern

## Aufgabe
Verbessere die Rolle `$ARGUMENTS` (z. B. `decomposer --model lokal`) im Dialog: messen, eine
gezielte Änderung vorschlagen, erneut messen und nur bei nachgewiesener Verbesserung übernehmen
(SPEC-0055, Ratchet-Regel).

## Regeln – verbindlich
- Lies NIE Pfade mit dem Segment `holdout` (`.sdd/holdout/`, `blueprint/holdout/`) und nutze nie
  `--include-holdout`. Holdout-Fälle entscheiden über die Übernahme; du siehst nur ihr Aggregat.
- Ändere keine Fälle (`case.yaml`, `input/`, `expected/`, `hidden/`, `reference/`, `mutants/`) und
  keine Checks, um einen Score zu verbessern. Neue Fälle entstehen nur über
  `sdd role case capture` oder ausdrücklich auf Wunsch des Nutzers.
- Je Iteration genau **eine** Änderung (Prompt, Kontextquellen, Budgets oder Parameter), mit
  Hypothese. Das `output_schema` änderst du nicht (Contract-Änderung nach SPEC-0053).
- Höchstens 3 Iterationen, außer der Nutzer erlaubt mehr.

## Schritt 1: Baseline
```bash
sdd role eval <rolle> [--model PROFIL] --runs 3
```
Merke dir den Report-Pfad. Liegt `baseline.json` der Rolle vor, ist sie der Vergleichsstand;
sonst dient dieser Report als Ausgangspunkt. Gruppiere die gescheiterten **sichtbaren** Fälle nach
Ursache (welche Checks scheitern, was die Ausgaben gemeinsam haben). Lies dafür den Report und die
sichtbaren Fälle unter `.sdd/roles/<rolle>/cases/`.

## Schritt 2: Kandidat
Kopiere die Rollendatei (`.sdd/roles/<rolle>.md`, im sdd-framer-Repo
`tool/sdd_cli/blueprint/roles/<rolle>.md`) nach `.sdd/roles/<rolle>/candidate.md` und ändere genau
eine Sache. Schreibe die Hypothese auf: welche Fälle sich warum verbessern sollen.

## Schritt 3: Messen und vergleichen
```bash
sdd role eval <rolle> [--model PROFIL] --version .sdd/roles/<rolle>/candidate.md --runs 3
sdd role compare <baseline-report-oder-baseline.json> <kandidat-report>
```
- `reject`: Begründung lesen, zurück zu Schritt 2 mit einer anderen Änderung.
- `accept`: weiter mit Schritt 4.

## Schritt 4: Übernahme nach Bestätigung
Lege dem Nutzer vor: Diff der Rollendatei, Hypothese, Scores vorher → nachher (gesamt, Holdout-
Aggregat, je sichtbarem Fall). Erst nach Zustimmung:
```bash
sdd role accept <rolle> --report <kandidat-report>
```
`accept` erhöht die Version, ersetzt `baseline.json` und ergänzt den CHANGELOG der Rolle. Lösche
danach die Kandidatendatei. `--force --reason` nur auf ausdrücklichen Wunsch des Nutzers.

## Schritt 5: Abschluss
Zeige: neue Version, Score vorher → nachher, verworfene Hypothesen. Schlage vor, Fehlschläge aus
echten Runs mit `sdd role case capture <run_id> <task_id|request_id>` als neue Fälle aufzunehmen.
