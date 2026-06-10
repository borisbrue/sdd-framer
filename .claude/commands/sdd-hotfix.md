---
scope: hotfix-workflow
---
<!-- skill: sdd-hotfix | version: 0.1.0 | sdd-blueprint: true | updated: 2026-05-30 -->

# /sdd-hotfix – Schlanker Hotfix-Flow

## Aufgabe
Führt durch den minimalen Hotfix-Zyklus: Bug beschreiben → Fix implementieren →
Einspielen. Kein SOLID-Check, keine Contracts, keine Tests, kein Container.

`` enthält optional eine kurze Bug-Beschreibung. Falls leer: nachfragen.

## Schritt 1: Bug beschreiben

Falls `` leer: "Was soll gefixt werden? (kurze Beschreibung)"

Dann:
```bash
sdd hotfix start "<beschreibung>"
```

Zeige die vergebene HF-ID und warte nicht — fahre sofort fort.

## Schritt 2: Fix implementieren

Analysiere den Bug anhand der Beschreibung und des aktuellen Codestands:
- Finde die betroffene(n) Datei(en)
- Implementiere den minimalen Fix direkt (Read → Edit/Write)
- Kein Refactoring, keine Abstraktion über das Nötige hinaus

Zeige nach dem Fix kurz: welche Datei(en) geändert wurden und warum.

## Schritt 3: Einspielen

```bash
git add <geänderte Dateien>
sdd hotfix finalize <HF-ID>
```

Zeige den Commit-Hash.

Falls `sdd hotfix finalize` fehlschlägt (z.B. nichts staged):
→ Hinweis: "Keine staged Changes – füge zuerst Dateien mit `git add` hinzu."

## Schritt 4: Zusammenfassung

```
Hotfix abgeschlossen: HF-XXXX
  Fix:    <Beschreibung was geändert wurde>
  Commit: <hash>
  Dateien: <liste>
```

## Konventionen
- Minimaler Fix — keine Gelegenheitsrefactorings
- Keine neuen Tests, keine Contracts, kein SOLID-Check (SPEC-0031 Gate-Ausnahme)
- Commit-Message wird automatisch von `sdd hotfix finalize` gesetzt