---
id: SPEC-0136
title: "Kontextbasiertes Routing lokal/Cloud"
status: approved
---
# SPEC-0136: Kontextbasiertes Routing lokal/Cloud

## 1. Kontext
Kleine Tasks sollen ein lokales Modell nutzen, große die Cloud. Entscheidend ist, ob der Kontext
eines Tasks samt einer Reserve für die Antwort in das Kontextfenster des lokalen Modells passt.

## 2. Nicht-Ziele
- Kein exakter Tokenizer, keine Netzwerkaufrufe, keine Abhängigkeiten außer der Standardbibliothek.

## 4. Funktionale Anforderungen

- **FR-01:** `TaskContext` ist eine Dataclass mit den Feldern `task_description` und
  `spec_section` (Strings, Default `""`) sowie `contract_texts`, `test_stub_texts` und
  `code_file_texts` (Listen von Strings, Default jeweils eine eigene leere Liste).
  `full_text()` verbindet in dieser Reihenfolge Beschreibung, Spec-Abschnitt, Contracts,
  Test-Stubs und Code-Dateien mit genau einem `"\n"`; leere Teile werden ausgelassen (keine
  doppelten Zeilenumbrüche, kein führender oder abschließender Umbruch).
- **FR-02:** `count_task_tokens(ctx)` schätzt die Tokenzahl ohne Netzwerk: ein Token je
  angefangene 4 Zeichen von `full_text()` (aufgerundet; leerer Text ergibt 0).
- **FR-03:** `ContextSizeRoutingStrategy(context_window, context_reserve_tokens, enabled,
  counter=None)`: `route(ctx)` liefert `"local"`, wenn geschätzte Tokens plus Reserve das
  Kontextfenster nicht überschreiten (Gleichstand ist noch `"local"`), sonst `"cloud"`. Der
  optionale `counter` ersetzt `count_task_tokens`.
- **FR-04:** Ist `enabled` falsch, liefert `route` immer `"cloud"`, ohne den Zähler aufzurufen.
  Die Entscheidung ist deterministisch.
