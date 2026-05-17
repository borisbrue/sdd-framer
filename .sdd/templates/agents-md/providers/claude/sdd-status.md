<!-- skill: sdd-status | version: 0.1.0 | sdd-blueprint: true | updated: 2026-05-16 -->

# /sdd-status – Lifecycle-Status und Blockaden

## Aufgabe
Zeige den vollständigen Lifecycle-Status aller Specs, gruppiert nach Fortschritt.
Für jeden Blocker: konkreter nächster Schritt.
`$ARGUMENTS` kann `--spec SPEC-XXXX` (Einzelspec) oder leer (alle) sein.

## Schritt 1: Vorbedingung
Prüfe ob `.sdd/config.yaml` existiert. Falls nicht: Fehlermeldung und abbrechen.

## Schritt 2: Status-Daten laden
```bash
sdd status-check
```
Und alle Spec-Frontmatter lesen um Status + Contracts + Tests zu kennen.

## Schritt 3: Gruppierte Ausgabe

**Blockiert** – Specs die nicht weiter können:
```
🔴 BLOCKIERT (N)
  SPEC-0012  Nachrichtenserver     status: draft  | Fehlt: kein Contract
  SPEC-0018  Claude Skills         status: draft  | Fehlt: CON-0057, CON-0058
```
Für jeden Blocker: konkreter nächster Schritt, z.B.:
"→ Erstelle Contract: /sdd-new contract (SPEC-0012)"

**In Arbeit** – Specs in draft oder in-progress:
```
🟡 IN ARBEIT (N)
  SPEC-0019  TDD-Phase             status: in-progress  | seit 0h
  SPEC-0020  /sdd-implement        status: draft
```

**Bereit für Execution Gate** – approved + alle Contracts approved:
```
🟢 BEREIT FÜR GATE (N)
  SPEC-0014  Execution Gate        status: approved
  → Starte: sdd orchestrate --spec SPEC-0014
```

**Abgeschlossen:**
```
✅ IMPLEMENTIERT (N)
  SPEC-0001 … SPEC-0011, SPEC-0014, SPEC-0015, SPEC-0016, SPEC-0019
```

## Schritt 4: Einzelspec-Ansicht (wenn --spec SPEC-XXXX)
Zeige detaillierten Status:
- Frontmatter-Felder: status, started_at, contracts, tests
- Gate-Status: `.sdd/pipeline/SPEC-XXXX-gate.json` wenn vorhanden
- SOLID-Check: `.sdd/patterns/SPEC-XXXX-patterns.json` wenn vorhanden
- Nächster Schritt (konkret)

## Schritt 5: Aktions-Vorschläge
Am Ende immer 1–3 konkrete nächste Schritte:
```
Empfohlene nächste Schritte:
  1. /sdd-new contract  → Contract für SPEC-0012 erstellen
  2. sdd start SPEC-0019  → TDD-Implementierung starten
  3. /sdd-validate  → 9 offene Fehler beheben
```
