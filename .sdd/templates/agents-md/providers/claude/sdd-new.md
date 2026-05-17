<!-- skill: sdd-new | version: 0.1.0 | sdd-blueprint: true | updated: 2026-05-16 -->

# /sdd-new – Neuen SDD-Spec, Contract, Test oder ADR erstellen

## Aufgabe
Führe den Nutzer interaktiv durch die Erstellung eines neuen SDD-Dokuments.
`$ARGUMENTS` enthält den Typ: `spec`, `contract`, `test` oder `adr`.

## Schritt 1: Typ bestimmen
Falls `$ARGUMENTS` leer: frage "Was möchtest du erstellen? (spec / contract / test / adr)"
Akzeptiere Abkürzungen: s=spec, c=contract, t=test, a=adr.

Prüfe ob `.sdd/config.yaml` existiert. Falls nicht: Fehlermeldung und abbrechen.

## Schritt 2a: SPEC erstellen
Stelle maximal 6 Fragen (eine nach der anderen, warte auf Antwort):
1. **Feature/Problem:** Welches Problem löst dieses Feature? (→ Titel + Kontext)
2. **Betroffene:** Wer nutzt das? Beschreibe 1–2 Nutzergruppen. (→ User Stories)
3. **Erfolgskriterien:** Was ist der messbare Erfolg? (→ Acceptance Criteria)
4. **Nicht-Ziele:** Was ist explizit NICHT im Scope?
5. **Abhängigkeiten:** Welche SPEC-IDs hängen davon ab? (leer = keine)
6. **Priorität:** high / medium / low (Default: medium)

Nächste freie ID ermitteln:
```bash
ls .sdd/specs/ | grep "^SPEC-" | sort | tail -1
```
Erhöhe die Nummer um 1 und forme: `SPEC-XXXX`.

Lese eine bestehende Spec als Formatreferenz (z.B. die letzte SPEC-Datei).

Generiere ein vollständiges SPEC-Dokument mit:
- YAML-Frontmatter: id, title, status: draft, owner, created/updated (heute), version: 0.1.0
- Pflichtabschnitte: Kontext & Motivation, Zielsetzung (inkl. Erfolgskriterien + Nicht-Ziele),
  Architektur & Design Patterns (min. 2 Patterns mit Begründung + Refactoring-Guru-Link),
  Funktionale Anforderungen (FR-01, FR-02, …), User Stories, Contracts (leer), Tests (leer),
  Implementierungsreihenfolge, Offene Fragen, Änderungshistorie

Zeige das Dokument zur Bestätigung. Erst nach "ja" / "ok" / "speichern":
```bash
# Datei schreiben (slug aus Titel ableiten)
```
Führe danach aus: `sdd validate --file .sdd/specs/SPEC-XXXX-<slug>.md`
Bei Fehlern: erklären und korrigieren. Erst dann endgültig speichern.

## Schritt 2b: CONTRACT erstellen
Fragen:
1. Welche SPEC-ID soll verknüpft werden? (z.B. SPEC-0001)
2. Welcher Typ? api / behavior / data / performance
3. Was garantiert dieser Contract? (ein Satz)

Nächste CON-ID ermitteln analog zu SPEC. Template laden:
```bash
cat .sdd/templates/contract/<typ>-*.md | head -30
```
Generiere Contract-Dokument, zeige zur Bestätigung, speichere nach OK.

## Schritt 2c: TEST erstellen
Fragen:
1. Welche SPEC-ID?
2. Welcher Contract (CON-ID)?
3. Teststufe: unit / contract / acceptance / performance
4. Was genau wird geprüft? (ein Satz)

Template: `.sdd/templates/test/default.md`. Speichere in `tests/<stufe>/`.

## Schritt 2d: ADR erstellen
Fragen:
1. Welche Entscheidung wird dokumentiert? (Titel)
2. Kontext und Problem?
3. Entscheidung und Begründung?
4. Konsequenzen?

Template: `.sdd/templates/adr/default.md`. Nächste ADR-ID ermitteln.
