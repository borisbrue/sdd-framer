# SPEC-0104: Run-Verzeichnis der Pipeline

## 1. Zusammenfassung

Jeder Pipeline-Lauf bekommt ein Verzeichnis `<root>/.sdd/runs/<SPEC-ID>/<run_id>/`. Darin liegt
`state.json` (nach jedem Übergang neu geschrieben) und `events.jsonl` (nur angehängt). Ein Absturz
mitten im Schreiben darf `state.json` nie halb geschrieben hinterlassen.

## 3. Nicht-Ziele

- Kein Locking zwischen Prozessen, keine Aufräumlogik für alte Runs.

## 4. Funktionale Anforderungen

- **FR-01:** `new_run_id(spec_id)` liefert `<SPEC-ID>-<YYYYMMDDTHHMMSS>-<suffix>`; der Zeitstempel ist
  die aktuelle Zeit in **UTC**, der Suffix besteht aus Kleinbuchstaben/Ziffern und ist zufällig, so
  dass zwei Aufrufe in derselben Sekunde verschiedene IDs liefern. `RUN_ID_RE` ist ein kompilierter
  regulärer Ausdruck, der genau solche IDs (Spec-ID der Form `SPEC-` + vier Ziffern) erkennt und
  die Spec-ID als Gruppe 1 liefert. `now()` liefert die UTC-Zeit als `YYYY-MM-DDTHH:MM:SSZ`.
- **FR-02:** `atomic_write_json(path, data)` legt fehlende Elternverzeichnisse an und schreibt `data`
  als JSON (UTF-8, Nicht-ASCII-Zeichen unescaped, Einrückung 2, abschließender Zeilenumbruch).
  Geschrieben wird in eine temporäre Datei im selben Verzeichnis, die anschließend per
  `os.replace` die Zieldatei ersetzt. Scheitert das Schreiben (z. B. nicht serialisierbare
  Daten), bleibt eine bestehende Zieldatei unverändert, es bleibt keine temporäre Datei zurück
  und die ursprüngliche Ausnahme wird weitergereicht.
- **FR-03:** `RunStore.create(root, spec_id, run_id=None)` legt das Run-Verzeichnis an und liefert
  den Store (Attribute `root`, `spec_id`, `run_id`, `dir`). Ohne `run_id` wird eine neue erzeugt.
  Eine vorgegebene `run_id`, die nicht `RUN_ID_RE` entspricht oder zu einer anderen Spec gehört,
  führt zu `ValueError`. Existiert das Verzeichnis bereits, schlägt `create` mit
  `FileExistsError` fehl.
- **FR-04:** `RunStore.open(root, run_id)` öffnet einen bestehenden Run; die Spec-ID wird aus der
  Run-ID abgeleitet. Ungültige Run-IDs und Runs ohne `state.json` führen zu `RunNotFound`.
- **FR-05:** `write_state(state)` setzt `state["updated_at"] = now()` und schreibt `state.json`
  atomar (FR-02); `read_state()` liest es zurück.
- **FR-06:** `event(type_, **felder)` hängt eine JSON-Zeile an `events.jsonl` an, mit den Schlüsseln
  `ts` (`now()`), `run_id`, `type` und allen Feldern, deren Wert nicht `None` ist.
  `read_jsonl(name)` liefert die Zeilen einer JSONL-Datei im Run-Verzeichnis als Liste von dicts,
  überspringt Leerzeilen und liefert `[]`, wenn die Datei fehlt.
