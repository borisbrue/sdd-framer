---
scope: lifecycle-status
---
<!-- skill: sdd-status | version: 0.1.1 | sdd-blueprint: true | updated: 2026-05-29 -->

# /sdd-status – Lifecycle-Status und Blockaden

## Aufgabe
Zeige den vollständigen Lifecycle-Status aller Specs.
`$ARGUMENTS` kann `--spec SPEC-XXXX` (Einzelspec) oder leer (alle) sein.

## Schritt 1: Vorbedingung
Prüfe ob `.sdd/config.yaml` existiert. Falls nicht: "Kein SDD-Projekt. 'sdd init' zuerst." und abbrechen.

## Schritt 2: Status ausgeben

```bash
sdd status $ARGUMENTS 2>&1
```

Zeige die Ausgabe direkt. Kein manuelles Parsen, kein Neuaufbau der Tabelle.

## Schritt 3: Aktions-Vorschläge
Leite aus der Ausgabe 1–3 konkrete nächste Schritte ab und zeige sie am Ende:

```
Empfohlene nächste Schritte:
  1. ...
```