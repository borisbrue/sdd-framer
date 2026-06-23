---
id: CON-0187
project: PRJ-0001
title: "Sichtbare LLM-Fehler in SOLID-Check und Pattern-Vorschlägen"
type: behavior
format: gherkin
spec: SPEC-0050
version: 0.1.0
status: approved
artifact: "contracts/behavior/llm-error-visibility.feature"
tests: [TST-0213]
---

# Contract: Sichtbare LLM-Fehler in SOLID-Check und Pattern-Vorschlägen

> **Spec:** SPEC-0050 · **Typ:** Verhalten (Gherkin) · **Status:** draft

## Zweck

Schreibt fest, dass `pattern.py` und `solid.py` LLM-Infrastruktur-Fehler sichtbar melden, statt
sie als leeres bzw. „sauberes" Ergebnis zu tarnen (FR-03, FR-04).

## Garantien

Die Szenarien im Artifact (`contracts/behavior/llm-error-visibility.feature`) sind ausführbare
Spezifikation und MÜSSEN durch automatisierte Tests abgedeckt sein.

## Invarianten

- **INV-01:** Ein LLM-Fehler beim Pattern-Vorschlag führt zu einer sichtbaren Warnung und NICHT
  zur Ausgabe „Keine Pattern-Vorschläge generiert".
- **INV-02:** Ein LLM-Fehler beim SOLID-Check führt zu einer sichtbaren Warnung und NICHT zur
  Darstellung „compliant".
- **INV-03:** Bei nutzbarem Provider bleibt das bisherige Ergebnisverhalten (echte Vorschläge /
  echte SOLID-Befunde) unverändert.

## Geltungsbereich

- **In Scope:** Fehler-Sichtbarkeit/Ergebnis-Semantik von `pattern.py` und `solid.py`.
- **Out of Scope:** Provider-Auflösung selbst (→ CON-0186).
