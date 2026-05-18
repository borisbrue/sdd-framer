<!-- skill: sdd-implement | version: 0.1.0 | sdd-blueprint: true | updated: 2026-05-16 -->

# /sdd-implement – TDD-Implementierungsphase

## Aufgabe
Implementiere das Feature für die angegebene SPEC vollständig nach TDD.
`$ARGUMENTS` enthält die SPEC-ID (z.B. SPEC-0020).

⚠️ KRITISCH: `.sdd/holdout/` wird NIEMALS gelesen. Kein Holdout-Inhalt darf
in den Implementierungskontext einfließen. Dies sichert die Evaluator-Isolation.

## Schritt 1: Vorbedingungen prüfen
- Existiert `.sdd/config.yaml`? Falls nicht: "Kein SDD-Projekt. 'sdd init' zuerst."
- Lese Frontmatter der Spec. `status` muss `in-progress` sein.
  Falls nicht: "Führe zuerst 'sdd start $ARGUMENTS' aus." und abbrechen.
- Prüfe ob sdd CLI verfügbar: `which sdd`

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

## Schritt 3: Implementierungsplan erstellen
Analysiere Spec + Contracts und entwirf einen Plan:
- Welche Dateien/Module werden erstellt oder geändert?
- Welche Klassen/Funktionen sind nötig?
- Reihenfolge (Abhängigkeiten zuerst)

Zeige den Plan und warte auf Bestätigung bevor Code geschrieben wird.

## Schritt 4: TDD-Zyklus
Für jede logische Einheit im Plan:

1. Schreibe Implementierungscode (auf Basis von Spec + Contracts, NICHT Holdout)
2. Führe Tests aus:
   ```bash
   pytest tests/ -x --tb=short
   ```
3. Bei Fehler: analysiere den Traceback, korrigiere den Code, wiederhole
4. Bei >3 Iterationen ohne Fortschritt: pausiere und frage den Nutzer
5. Bei grünen Tests: weiter zur nächsten logischen Einheit

Zyklus endet wenn alle Test-Stubs ohne `NotImplementedError` durchlaufen.

## Schritt 5: Abschluss
```bash
sdd validate
```
Erkläre und behebe Validierungsfehler.

Zeige Zusammenfassung:
```
✓ Implementierung abgeschlossen: SPEC-XXXX
  N Tests grün | Validierung sauber

Nächster Schritt (autonomer Pfad):
  sdd orchestrate --spec SPEC-XXXX [--base-url http://localhost:8000]
  → Evaluator prüft Holdout-Szenarien mit unabhängigem LLM
```

## Konventionen
- Keine Kommentare außer wenn WHY nicht offensichtlich
- SOLID-Regeln aus Pattern-Register beachten
- Keine neuen Tests schreiben – nur vorhandene Stubs implementieren
- Kein automatisches git commit
