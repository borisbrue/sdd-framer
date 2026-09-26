---
id: SPEC-0104
title: "Schreibgrenzen für den Implementierer"
status: approved
---
# SPEC-0104: Schreibgrenzen für den Implementierer

## 1. Kontext

Jeder Task nennt in `allowed_paths` die Dateien, die der Implementierer ändern darf, und in
`test_file` den Test, den er grün machen soll. Bevor seine Ausgabe geschrieben wird, prüft
die Pipeline jeden Pfad.

## 4. Funktionale Anforderungen

- **FR-01:** `path_violations(paths, allowed, test_file=None)` gibt die Pfade aus `paths`
  zurück, die nicht geschrieben werden dürfen, in der Reihenfolge der Eingabe. Ein Pfad ist
  erlaubt, wenn er auf mindestens eines der Muster in `allowed` passt (`fnmatch`-Semantik:
  `*` passt auch über `/` hinweg). Ist `allowed` leer, ist kein Pfad erlaubt.
- **FR-02:** Unabhängig von `allowed` verboten sind: die Testdatei `test_file` (der
  Implementierer darf seinen Test nicht ändern) und alles unter dem Verzeichnis `.sdd/`.
  Andere Verzeichnisse, die nur mit `.sdd` beginnen (z. B. `.sddit/config.toml`), sind
  nicht betroffen.
- **FR-03:** Ebenfalls immer verboten sind absolute Pfade (beginnen mit `/`) und Pfade mit
  einem `..`-Segment (`pkg/../secrets.py`), auch wenn ein Muster wie `pkg/*` oder `*`
  darauf passt. Dateinamen, die `..` nur enthalten (`pkg/v1..2.txt`), sind kein Segment.

## 5. Nicht-Ziele

- Auflösen von Symlinks oder Zugriff auf das Dateisystem.
