<!-- skill: sdd-implement | version: 0.2.0 | sdd-blueprint: true | updated: 2026-05-19 -->

# /sdd-implement – TDD-Implementierungsphase

## Aufgabe
Implementiere das Feature für die angegebene SPEC vollständig nach TDD.
`$ARGUMENTS` enthält die SPEC-ID (z.B. SPEC-0020).

⚠️ KRITISCH: `.sdd/holdout/` wird NIEMALS gelesen. Kein Holdout-Inhalt darf
in den Implementierungskontext einfließen. Dies sichert die Evaluator-Isolation.

## Schritt 1: Vorbedingungen prüfen
- Existiert `.sdd/config.yaml`? Falls nicht: "Kein SDD-Projekt. 'sdd init' zuerst."
- Lese Frontmatter der Spec. Falls `status` nicht `in-progress`:
  - Falls `status == approved`: führe automatisch aus:
    ```bash
    sdd start $ARGUMENTS
    ```
    `▶ sdd start $ARGUMENTS` (Status → in-progress)
  - Falls `status` ein anderer Wert (z.B. `draft`, `deprecated`):
    "✗ Spec hat Status '$STATUS' – Implementierung nicht möglich." und abbrechen.
- Prüfe ob sdd CLI verfügbar: `which sdd`
- Prüfe ob der Dev-Container läuft:
  ```bash
  podman inspect --format '{{.State.Status}}' sdd-dev-$(echo $ARGUMENTS | tr '[:upper:]' '[:lower:]' | tr '-' '-')
  ```
  Falls nicht `running`: "Container nicht gestartet – führe 'sdd start $ARGUMENTS' erneut aus." und abbrechen.

## Schritt 1b: Feature-Branch erstellen
```bash
git checkout -b feat/$ARGUMENTS 2>/dev/null || git checkout feat/$ARGUMENTS
```
`▶ Branch feat/$ARGUMENTS` erstellt oder ausgecheckt (kein Fehler wenn bereits vorhanden).

## Schritt 2: Kontext laden (Allowlist – kein Holdout)
Lese folgende Dateien (und NUR diese):
1. `.sdd/specs/$ARGUMENTS-*.md` – vollständiger Spec-Inhalt
2. Alle CON-IDs aus `contracts:`-Frontmatter → zugehörige Contract-Dateien in `.sdd/contracts/`
3. `.sdd/patterns/$ARGUMENTS-patterns.json` – falls vorhanden
4. `AGENTS.md` – falls vorhanden (zeige [WARN] wenn fehlend)
5. Test-Stub-Dateien: `tests/**/test_tst_*.py` oder Dateien aus TST-`artifact`-Feldern

**Nicht lesen:** `.sdd/holdout/` – nie, unter keinen Umständen.

Fasse den geladenen Kontext kurz zusammen:
- Spec: Titel, Status, N Contracts, M Test-Stubs
- Contracts: [CON-IDs]
- Pattern-Register: [Pattern-Namen falls vorhanden]

## Schritt 3: Implementierungsplan via Decompose laden
```bash
sdd decompose $ARGUMENTS
```
`▶ sdd decompose $ARGUMENTS`

Falls die Task-Liste leer ist (0 Tasks):
"✗ Keine Tasks gefunden – prüfe Spec-Inhalt." und abbrechen.

Die Tasks aus dem Decompose-Plan werden sequenziell als Implementierungsplan genutzt
(kein `sdd distribute` — das bleibt `sdd orchestrate` vorbehalten).

Zeige den Plan und starte sofort mit der Implementierung — keine Bestätigung erforderlich.

## Schritt 4: TDD-Zyklus (im Container)

Code wird auf dem Host-Filesystem geschrieben (Read/Edit/Write-Tools).
Tests laufen **im Container** via `sdd dev exec` — vollständig isoliert,
keine Host-Berechtigungen nötig.

Für jede logische Einheit im Plan:

1. Schreibe Implementierungscode (auf Basis von Spec + Contracts, NICHT Holdout)
2. Führe Tests im Container aus:
   ```bash
   sdd dev exec $ARGUMENTS pytest tests/ -x --tb=short
   ```
3. Bei Fehler: analysiere den Traceback, korrigiere den Code, wiederhole
4. Bei >3 Iterationen ohne Fortschritt: stoppe mit Fehlerbericht (was versucht wurde, was fehlschlägt) — kein User-Prompt
5. Bei grünen Tests: weiter zur nächsten logischen Einheit

Zyklus endet wenn alle Test-Stubs ohne `NotImplementedError` durchlaufen.

**Hinweis:** `sdd dev exec` benötigt pip-Setup nur beim ersten Aufruf. Wenn der
Container neu ist, einmalig ausführen:
```bash
sdd dev exec $ARGUMENTS bash -c "pip install -q --no-user --no-cache-dir -e '/workspace/' -e '/workspace/tool/[dev]'"
```

## Schritt 5: Finalisierung

Führe zuerst `sdd validate` aus und behebe alle Fehler.

`sdd finalize` startet keinen Container selbst — der Container muss bereits laufen.
Falls kein Container läuft erscheint:
"✗ Dev-Container nicht gefunden – starte ihn mit 'sdd start $ARGUMENTS'"

**Versuch 1 und 2:**
```bash
sdd finalize $ARGUMENTS
```
`▶ sdd finalize $ARGUMENTS`

Bei fehlgeschlagenen Container-Tests: Traceback analysieren, Code korrigieren,
erneut im Container testen (Schritt 4), dann `sdd finalize $ARGUMENTS` wiederholen.

**Dritter fehlgeschlagener Versuch (Container-Fehler):**
Führe automatisch aus:
```bash
sdd finalize $ARGUMENTS --skip-container
```
⚠ Container-Tests wurden übersprungen — Commit und PR laufen normal durch.

Zeige den `FinalizeReport` (Branch, Commit-Hash, PR-URL oder lokaler PR-Pfad).

## Schritt 6: Holdout-Evaluation (im Container)

Nach erfolgreichem `sdd finalize` die Holdout-Szenarien evaluieren.
`sdd evaluate` läuft im Dev-Container (API-Key wurde beim Start übergeben).

```bash
sdd dev exec $ARGUMENTS bash -c \
  "pip install -q --no-user --no-cache-dir -e '/workspace/tool/[evaluate]' > /dev/null && \
   sdd evaluate --base-url $SDD_EVAL_BASE_URL --spec $ARGUMENTS"
```

**Retry-Loop (max 3 Versuche):**

| Versuch | Ergebnis | Aktion |
|---------|----------|--------|
| 1–2 | fehlgeschlagen | Traceback analysieren, Code korrigieren, `sdd finalize` + erneut evaluieren |
| 3 | fehlgeschlagen | `sdd evaluate ... --final-attempt` ausführen → Status → `evaluation-failed`, Bericht anzeigen, Nutzer informieren |
| beliebig | bestanden | Fertig |

Beim 3. fehlgeschlagenen Versuch `--final-attempt` setzen:
```bash
sdd dev exec $ARGUMENTS bash -c \
  "sdd evaluate --base-url $SDD_EVAL_BASE_URL --spec $ARGUMENTS --final-attempt"
```

Der Nutzer sieht dann einen Fehlerbericht und entscheidet ob die Spec überarbeitet
oder die Holdout-Kriterien angepasst werden sollen.

## Konventionen
- Keine Kommentare außer wenn WHY nicht offensichtlich
- SOLID-Regeln aus Pattern-Register beachten
- Keine neuen Tests schreiben – nur vorhandene Stubs implementieren
- Kein automatisches git commit
