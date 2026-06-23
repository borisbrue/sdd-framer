---
id: CON-0183
project: PRJ-0001
title: "PatternRegistry.catalog_summary() – Ausgabeformat"
type: data
format: markdown
spec: SPEC-0048
version: 0.1.0
status: approved
artifact: ""
tests:
- TST-0210
---

# Contract: PatternRegistry.catalog_summary() – Ausgabeformat

> **Spec:** SPEC-0048 · **Typ:** Daten (Schema) · **Status:** draft

## Zweck

Definiert das Textformat, das `PatternRegistry.catalog_summary()` zurückgibt — die
kompakte, LLM-taugliche Zusammenfassung des globalen Pattern-Katalogs
(`.sdd/patterns/_catalog.json`).

## Signatur

```python
def catalog_summary(
    self,
    max_entries: int = 10,
    exclude_spec_id: str | None = None,
) -> str: ...
```

## Format

Jeder Eintrag ist eine Zeile der Form:

```
- {pattern_name} ({spec_id}): {reason_truncated}
```

Mehrere Zeilen werden mit `\n` verbunden. Es gibt keinen Header/Footer — die
aufrufende Stelle (`_build_pattern_prompt`, `/sdd-implement` Schritt 2) übernimmt
die Einbettung in den jeweiligen Abschnittstitel.

## Invarianten

- **INV-01:** Rückgabetyp ist immer `str` — nie `None`. Bei leerem/fehlendem Katalog
  oder wenn nach Ausschluss von `exclude_spec_id` nichts übrig bleibt: leerer String `""`.
- **INV-02:** `reason_truncated` ist die `acceptance_reason` des Katalogeintrags,
  gekürzt auf maximal 120 Zeichen. Wird gekürzt, endet die Zeile auf `…`
  (Kürzung exklusive des `…`-Zeichens, d.h. max. 120 sichtbare Zeichen + `…`).
- **INV-03:** Maximal `max_entries` Zeilen werden zurückgegeben, sortiert nach
  `accepted_at` absteigend (neueste zuerst).
- **INV-04:** Einträge mit `spec_id == exclude_spec_id` werden vor der `max_entries`-
  Begrenzung herausgefiltert (Ausschluss zählt nicht gegen das Limit anderer Einträge).
- **INV-05:** Ist `_catalog.json` nicht vorhanden oder nicht parsebar (ungültiges JSON),
  wird dies wie ein leerer Katalog behandelt (kein Fehler, kein Exception-Propagieren).

## Beispiele

**Gültig (2 Einträge, keine Kürzung nötig):**
```
- Observer (SPEC-0034): SSE-Streaming: TaskEventBus entkoppelt Statuswechsel von Subscriber-Typen.
- Repository (SPEC-0034): Kapselt tasks.json-Persistenz. Ermöglicht Austausch gegen DB ohne API-Änderung.
```

**Gültig (leerer Katalog):**
```
""
```

**Ungültig (und warum):**
```
None
```
→ Verstößt gegen INV-01 (Rückgabetyp muss immer `str` sein, auch im leeren Fall).

## Validierung

- Unit-Tests prüfen: leerer Katalog, 1 Eintrag, N > max_entries Einträge,
  Eintrag mit `acceptance_reason` > 120 Zeichen, `exclude_spec_id` greift korrekt,
  korrupte `_catalog.json` (kein valides JSON).
