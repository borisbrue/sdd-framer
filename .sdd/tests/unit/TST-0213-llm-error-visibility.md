---
id: TST-0213
project: PRJ-0001
title: "Sichtbare LLM-Fehler in pattern/solid statt stiller Degradierung"
level: unit
spec: SPEC-0050
contract: CON-0187
status: planned
framework: pytest
artifact: "tests/unit/test_tst_0213.py"
tags: [llm, pattern, solid, reliability]
---

# Test: Sichtbare LLM-Fehler in pattern/solid statt stiller Degradierung

> **Level:** unit · **Spec:** SPEC-0050 · **Contract:** CON-0187 · **Status:** planned

## Was wird geprüft?

Dass `pattern.py` und `solid.py` einen LLM-Infrastruktur-Fehler sichtbar machen, statt ihn als
leeres bzw. „compliant" Ergebnis zu tarnen.

## Testfälle

- **test_pattern_suggest_surfaces_llm_error:** `PatternSuggester` mit einem Provider, dessen
  `complete()` eine Exception wirft → der Fehler wird sichtbar gemacht (Warnung/Markierung im
  Ergebnis), das Ergebnis ist unterscheidbar von „echte 0 Vorschläge". *(RED bis Fix: aktuell
  `except Exception: suggestions = []` → ununterscheidbar leer.)*
- **test_solid_check_surfaces_llm_error:** SOLID-Analyse mit fehlschlagendem Provider →
  sichtbarer Fehler statt Darstellung „compliant".
- **test_happy_path_unchanged:** Mit funktionierendem (Fake-)Provider liefern beide echte
  Vorschläge bzw. Befunde – unverändertes Verhalten (INV-03).

> Hinweis: Der konkrete Sichtbarkeits-Mechanismus (Rückgabe-Flag vs. propagierte Exception vs.
> `[WARN]`-Ausgabe) wird in `/sdd-implement` festgelegt; die Tests prüfen das beobachtbare
> „nicht stumm schlucken".

## Abdeckung

CON-0187 INV-01…INV-03 · SPEC-0050 FR-03, FR-04.
