<!-- skill: sdd-implement | version: 1.1.0 | sdd-blueprint: true | updated: 2026-09-28 -->

# /sdd-implement – Implementierung über die Rollen-Pipeline

## Aufgabe
Implementiere `$ARGUMENTS` (SPEC-XXXX) über `sdd pipeline` (SPEC-0062). Die Pipeline zerlegt,
prüft Gates, lässt Holdouts laufen und finalisiert. Du übernimmst im Dialog die Rollen
`test_author`, `implementer` und `supervisor`; `decomposer` und `reviewer` laufen über die in
`llm.roles` konfigurierten Modelle.

⚠️ KRITISCH: `.sdd/holdout/` wird NIEMALS gelesen. Kein Holdout-Inhalt darf in den
Implementierungskontext einfließen. Die Pipeline liefert nur Holdout-Ergebnisse (Quote, IDs).

## Schritt 1: Vorbedingungen
- Existiert `.sdd/config.yaml`? Sonst: "Kein SDD-Projekt. 'sdd init' zuerst." und abbrechen.
- `which sdd` – die CLI muss verfügbar sein.
- Lies `status` aus dem Frontmatter der Spec:
  - `deprecated`: "✗ Spec ist deprecated – Implementierung nicht möglich." und abbrechen.
  - `in-progress`: Die Pipeline startet nur bei `approved`. Frage den Nutzer, ob die Spec
    zurück auf `approved` soll (erneute Freigabe wie im letzten Punkt von Schritt 2; die
    Gate-Phasen sind dann schon erfüllt), sonst abbrechen.

## Schritt 2: Review und Approve (nur bei `draft` oder `review`)
Die Freigabe der Spec verlangt jede Phase der Gate-Kette (CON-0025); fehlt eine, meldet sie
`✗ Phase '<phase>' noch nicht abgeschlossen`. Spawne einen Subagenten (Agent-Tool), der die Kette
in dieser Reihenfolge durchläuft:

> Führe das Review für $ARGUMENTS autonom durch, Schritt für Schritt:
> 1. `sdd spec review $ARGUMENTS` – schließt `spec-review` ab; SOLID-Analyse und Pattern-Vorschläge
>    (`sdd review spec $ARGUMENTS`) loggen, sinnvolle Patterns mit
>    `sdd review pattern accept $ARGUMENTS <Pattern> --reason "…"` annehmen.
> 2. Contracts prüfen (messbar, vollständig, atomar, widerspruchsfrei), dann
>    `sdd contract propose $ARGUMENTS CON-… CON-…` (Spec-ID zuerst, dann alle Contract-IDs).
> 3. `sdd contract analyze $ARGUMENTS CON-… CON-…`; offene Konflikte mit
>    `sdd conflict resolve|acknowledge $ARGUMENTS <CF-ID>` sachlich auflösen oder begründen.
> 4. `sdd test generate $ARGUMENTS CON-… CON-…` – Test-Rümpfe und `tests-generated`.
> 5. `sdd spec regression $ARGUMENTS` – bei Severity `error`: Abbruch mit Bericht.
> 6. Contracts mit `status: draft` auf `status: approved` setzen, wenn inhaltlich in Ordnung
>    (das Frontmatter allein ersetzt keine Gate-Phase), fehlende `fr_test_map`-Einträge ergänzen,
>    dann `sdd spec approve $ARGUMENTS`.

Scheitert das Review: Bericht zeigen und abbrechen mit
"✗ Automatisches Review fehlgeschlagen – '/sdd-review $ARGUMENTS' manuell ausführen."

## Schritt 3: Feature-Branch
```bash
git checkout -b feat/$ARGUMENTS 2>/dev/null || git checkout feat/$ARGUMENTS
```

## Schritt 4: Holdout-Szenarien sicherstellen
```bash
grep -rl "^spec: $ARGUMENTS" .sdd/holdout/ 2>/dev/null | wc -l
```
Bei 0 Treffern: Subagent (Agent-Tool) mit diesem Auftrag:

> Generiere Holdout-Szenarien für $ARGUMENTS. Lies ausschließlich die Spec und ihre Contracts
> (`contracts:` im Frontmatter). Nicht lesen: `tool/`, `web/`, `tests/`, `.sdd/holdout/`, Code.
> Je Contract 2–4 Szenarien (Happy Path und mindestens ein Fehlerfall) aus Nutzersicht:
> `sdd new holdout --contract <CON-ID> --spec $ARGUMENTS --title "<Titel>"`, dann `## Input`,
> `## Expected` und `## Evaluation Hint` befüllen.

Nur die Anzahl der angelegten HOL-IDs ausgeben, nie ihren Inhalt.

## Schritt 5: Kontext für deine Entscheidungen
Lies die Spec, ihre Contracts, `.sdd/patterns/$ARGUMENTS-patterns.json` (falls vorhanden) und
`AGENTS.md`. Aus `.sdd/patterns/_catalog.json` fasst du die in anderen Specs akzeptierten
Patterns zusammen. Ist die Zusammenfassung nicht leer, zeige eine Zeile
"Etablierte Patterns im Projekt: […]".

## Schritt 6: Run starten
```bash
sdd pipeline run $ARGUMENTS --auto --session test_author --session implementer --session supervisor
```
Mit laufendem Service für die Holdouts zusätzlich `--base-url $SDD_EVAL_BASE_URL`. Die Ausgabe
nennt die `run_id`.

| Exit | Bedeutung | Weiter |
|------|-----------|--------|
| 0 | Run abgeschlossen (Abschluss-Kette gelaufen) | Schritt 8 |
| 1 | Run angehalten oder Schritt gescheitert | Grund zeigen, Schritt 8 |
| 2 | Vorbedingung oder Konfiguration verletzt | Fehler zeigen, abbrechen |
| 3 | Der Run wartet auf dich | Schritt 7 |

## Schritt 7: Anfragen abarbeiten (Schleife bis Exit 0, 1 oder 2)
```bash
sdd pipeline status <run_id>
```
Im Run-Verzeichnis `.sdd/runs/$ARGUMENTS/<run_id>/` liegt genau eine offene Anfrage.

### 7a: Arbeitsauftrag (`pending-work.json`) – Rolle `test_author` oder `implementer`
Felder: `role`, `task_id`, `attempt`, `allowed_paths`, `test_file`, `sources` (Spec-Auszug,
Contracts, Task, Test-Ausgabe), `feedback` (Hinweise aus Review, Gates, Supervisor).
- `test_author`: Schreibe **nur** `test_file` – einen echten, roten Test, der die Task-FRs prüft
  (kein `skip`, kein `pass`).
- `implementer`: Ändere **nur** Dateien aus `allowed_paths`, bis der Test grün wird. Tests
  änderst du nicht.
- Andere Pfade lehnt die PathPolicy ab; `.sdd/holdout/` bleibt tabu.
Dann bestätigen:
```bash
sdd pipeline done <run_id>
```
Die Pipeline prüft RED/GREEN, Architektur- und Lint-Gates und den Review selbst; bei Feedback
kommt der nächste Auftrag an dieselbe Rolle.

### 7b: Entscheidung (`pending-decision.json`) – Rolle `supervisor`
Du entscheidest nur auf Basis der Fakten (`facts`) und nur mit Commands aus `allowed_commands`,
wie in `/sdd-supervise` beschrieben:

| Punkt | Wann | Command |
|-------|------|---------|
| S1 Zerlegung | Tasks decken alle FRs ab, sinnvoll geschnitten, testbar | `approve` |
| S1 | Lücken, zu grob, falsche Pfade | `revise` mit Begründung |
| S2 Eskalation | Fehler mit einem Hinweis lösbar | `retry_with_hint` |
| S2 | Modell überfordert | `reassign` |
| S2 | Task falsch geschnitten | `redecompose` |
| S3 Abnahme | je FR `erfüllt`, `teilweise` oder `fehlt` mit Beleg | `accept_frs` |
| S3 | Tests oder `facts.holdout` zeigen ein behebbares Problem | `reopen` |
| jederzeit | grundsätzliches Problem, erst nach Rückfrage beim Nutzer | `halt` |

```bash
sdd pipeline decide <run_id> --json '{"point": "S1", "command": "approve", "reason": "…"}'
```
Dem Nutzer legst du vor dem Absenden vor: jedes `halt` und jede S3-Abnahme mit einer FR
`teilweise` oder `fehlt`. Exit 2 bei `decide`/`done`: Meldung lesen, korrigieren, erneut senden.

## Schritt 8: Abschluss
```bash
sdd pipeline report <run_id>
```
Zeige dem Nutzer Ergebnis, PR-URL (Ereignis `finalize`), Holdout-Quote (`holdout`), Aufrufe und
Tokens je Rolle und deine Eingriffe. Zerlegung, Modellwahl je Task und PR erledigt die
Pipeline; einen eigenen TDD-Zyklus gibt es in diesem Skill nicht mehr.
