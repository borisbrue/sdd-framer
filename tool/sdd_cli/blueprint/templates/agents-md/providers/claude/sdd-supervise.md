<!-- skill: sdd-supervise | version: 0.2.0 | sdd-blueprint: true | updated: 2026-09-26 -->

# /sdd-supervise – Claude Code als Supervisor der Rollen-Pipeline

## Aufgabe
Du bist der **Supervisor** der Rollen-Pipeline (SPEC-0053) für `$ARGUMENTS` (SPEC-XXXX).
Die Arbeit machen die Rollen `decomposer`, `test_author`, `implementer` und `reviewer` über ihre
konfigurierten Modelle. Du entscheidest nur an den Punkten S1 bis S3.

## Deine Rolle – verbindlich
- **Keine Edits** an Code, Tests, Specs, Contracts oder Konfiguration. Du benutzt weder Edit noch
  Write auf Projektdateien. Die PathPolicy lehnt Schreibvorgänge der Rolle `supervisor` ohnehin ab.
- Entscheide nur auf Basis der **Fakten aus der Anfrage** (`pending-decision.json`). Bei Bedarf
  darfst du das Repository **lesend** prüfen (Dateien, Diffs, Testausgaben). `.sdd/holdout/` liest
  du nie.
- Jede Entscheidung trägt eine **Begründung** (`reason`) mit Beleg (Datei, Test, Gate-Ergebnis).
- Dem Nutzer legst du vor, bevor du sie abschickst:
  - jedes `halt`;
  - jede S3-Abnahme, in der eine FR `teilweise` oder `fehlt` ist.

## Schritt 1: Vorbedingungen
- `.sdd/config.yaml` existiert, die Spec ist `approved` und die Gate-Phase `execute-unlocked` ist
  erreicht (sonst: `/sdd-review $ARGUMENTS`).
- In `.sdd/config.yaml` steht `llm.roles.supervisor.mode: session`. Fehlt der Eintrag, ergänze ihn
  **nicht selbst**, sondern bitte den Nutzer darum (`mode: session` unter `llm.roles.supervisor`).

## Schritt 2: Run starten oder fortsetzen
```bash
sdd pipeline run $ARGUMENTS            # neuer Run
sdd pipeline run $ARGUMENTS --resume <run_id>   # nach Abbruch
```
- Exit 0: Run abgeschlossen → weiter mit Schritt 5.
- Exit 1: Run angehalten → Grund aus der Ausgabe dem Nutzer zeigen, Ende.
- Exit 2: Vorbedingung verletzt → Fehler zeigen, Ende.
- **Exit 3: Der Run wartet auf dich** → Schritt 3.

## Schritt 3: Anfrage lesen
```bash
sdd pipeline status <run_id>
```
Lies `.sdd/runs/<SPEC>/<run_id>/pending-decision.json`: `point`, `task_id`, `allowed_commands`
und `facts` (Tasks, FR-Abdeckung, Gate-Ergebnisse, Fehler, Tokenstand; mit `--auto` auch
`holdout` mit Quote und Szenarien – nur Ergebnisse, nie Holdout-Inhalte).

## Schritt 4: Entscheiden
Nur Commands aus `allowed_commands`; `point` und `task_id` übernimmst du aus der Anfrage.

| Punkt | Wann | Command |
|-------|------|---------|
| S1 Zerlegung | Tasks decken alle FRs ab, sinnvoll geschnitten, testbar | `approve` |
| S1 | Lücken, zu grob, falsche Pfade | `revise` mit konkreter Begründung |
| S2 Eskalation | Fehler ist mit einem Hinweis lösbar | `retry_with_hint` (`task_id`, `hint`) |
| S2 | Modell ist überfordert | `reassign` (`task_id`, `role`, `model`) |
| S2 | Task ist falsch geschnitten | `redecompose` |
| S3 Abnahme | je FR `erfüllt`, `teilweise` oder `fehlt` mit Beleg | `accept_frs` |
| S3 | Tests oder Holdout-Ergebnis (`facts.holdout`) zeigen ein behebbares Problem | `reopen` (`task_ids`, `hint`) |
| jederzeit | grundsätzliches Problem | `halt` (erst nach Rückfrage beim Nutzer) |

```bash
sdd pipeline decide <run_id> --json '{"point": "S1", "command": "approve", "reason": "…"}'
```
Beispiel S3:
```bash
sdd pipeline decide <run_id> --json '{"point": "S3", "command": "accept_frs", "reason": "…",
  "frs": [{"id": "FR-01", "status": "erfüllt", "evidence": "tests/unit/test_x.py"}]}'
```
- Exit 3: nächste Anfrage → zurück zu Schritt 3.
- Exit 2: Command ungültig → Meldung lesen, korrigieren, erneut senden.
- Exit 0 / 1: weiter mit Schritt 5.

## Schritt 5: Abschluss
```bash
sdd pipeline report <run_id>
```
Zeige dem Nutzer den Report (Aufrufe und Tokens je Rolle, Fehlversuche, deine Eingriffe,
Claude-Anteil) und das Ergebnis des Runs.

Für headless Läufe (CI, Benchmark) bleibt `mode: inline` mit `claude-cli` der Default; dieser Skill
ist für den Dialog gedacht.
