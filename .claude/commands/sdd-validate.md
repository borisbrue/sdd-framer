<!-- skill: sdd-validate | version: 0.1.0 | sdd-blueprint: true | updated: 2026-05-16 -->

# /sdd-validate – Validierung mit Fehler-Erklärungen

## Aufgabe
Validiere das SDD-Projekt und erkläre jeden Fehler auf Deutsch mit konkretem Fix-Vorschlag.
`$ARGUMENTS` kann sein: leer (alle), `--file SPEC-XXXX` oder `--file CON-XXXX`.

## Schritt 1: Vorbedingung
Prüfe ob `.sdd/config.yaml` existiert. Falls nicht: Fehlermeldung und abbrechen.

## Schritt 2: Validierung ausführen
```bash
sdd validate $ARGUMENTS
```
Speichere den vollständigen Output intern.

## Schritt 3: Ergebnisse klassifizieren

**Bei 0 Fehlern:**
```
✓ Validierung bestanden – keine Fehler gefunden.
```

**Bei Fehlern:** Für jeden Fehler eine strukturierte Erklärung ausgeben:

```
─── Fehler 1/N ─────────────────────────────────────────
Datei:   .sdd/specs/SPEC-0012-foo.md
Problem: Frontmatter ungültig: [] should be non-empty (Feld: contracts)
Warum:   Jede Spec braucht mindestens einen verknüpften Contract.
         Ohne Contract kann kein Execution Gate und kein Evaluator-Lauf
         durchgeführt werden.
Fix:     Erstelle einen Contract mit `/sdd-new contract` und trage
         die CON-ID in das `contracts:`-Feld ein.
         Alternativ: sdd new contract --spec SPEC-0012
Sofort?  [ja/nein]
```

**Fehlertypen und Erklärungen:**

- `[] should be non-empty` (contracts/tests):
  Pflichtfeld leer. Ohne Contracts/Tests keine Traceability und kein Gate.

- `Spec referenziert nicht existierenden Contract: CON-XXXX`:
  Die CON-ID im Frontmatter zeigt auf keine vorhandene Datei.
  Fix: Contract erstellen oder ID korrigieren.

- `Unbekannter Spec-Status`:
  Erlaubte Werte: draft, review, approved, in-progress, implemented, deprecated.

- `Lifecycle-Fehler FR-10/FR-11`:
  Erkläre den erlaubten Übergang: draft→review→approved→in-progress→implemented.

- `Taste Invariant verletzt: Inline-Suppress`:
  Ein Agent hat einen Linter-Fehler mit einem Suppress-Kommentar (z.B. `# noqa`,
  `// eslint-disable-next-line`) unterdrückt statt behoben.
  Fix: Entferne den Suppress-Kommentar und behebe die eigentliche Ursache.
  **Wichtig:** Inline-Disables erlauben es Agenten, Quality Gates zu umgehen —
  deshalb sind sie absolut verboten.

- `AGENTS.md Taste Invariants: Inline-Disable-Verbot nicht dokumentiert`:
  Die Sektion `## Taste Invariants` in AGENTS.md fehlt oder erwähnt das Verbot nicht.
  Fix: Das Inline-Disable-Verbot explizit in die Taste-Invariants-Sektion eintragen.

- `Unterverzeichnis enthält Quellcode aber kein AGENTS.md`:
  Ein Subkomponenten-Verzeichnis hat Quellcode aber kein eigenes AGENTS.md.
  Fix: `sdd new agents-md --subdir <verzeichnis>` ausführen und ausfüllen.

- Referenzielle Integrität (Contract ohne Spec, Test ohne Contract):
  Erkläre warum diese Verletzung den Traceability-Graph beschädigt.

## Schritt 4: Zusammenfassung
```
Zusammenfassung: N Fehler gefunden, M behoben.
Nächster Schritt: sdd validate (erneut prüfen)
```

Falls Fix angeboten und bestätigt: Datei direkt editieren und erneut validieren.
