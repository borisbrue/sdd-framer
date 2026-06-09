---
id: CON-0152
title: FrCoverageSpecification — FR→Test-Mapping-Garantie
type: behavior
format: markdown
spec: SPEC-0041
version: 0.1.0
status: approved
tests:
- TST-0178
---
`FrCoverageSpecification.is_satisfied_by(spec, tasks)` gibt für jedes FR
im Abschnitt „Funktionale Anforderungen" des Spec-Textes genau dann
`covered` zurück, wenn mindestens ein Task in der Task-Liste existiert
dessen `description` das FR (Form `FR-\d+`) enthält UND dessen `test_ids`
nicht leer ist.

**Garantien**

- Alle Bezeichner der Form `FR-\d+` im Abschnitt „Funktionale Anforderungen"
  werden extrahiert; FRs außerhalb dieses Abschnitts werden ignoriert.
- Ein FR gilt als `covered` wenn: mind. 1 Task hat das FR in `description`
  UND `task.test_ids` ist nicht leer. Alternativ: FR ist in
  `spec.frontmatter.fr_test_map` explizit auf eine TST-ID gemappt.
- `FrCoverageResult.uncovered` enthält alle FRs die keines der beiden
  Kriterien erfüllen — leere Liste bedeutet vollständige Abdeckung.
- Fehlt der Abschnitt „Funktionale Anforderungen" im Spec-Text vollständig,
  gibt die Methode `FrCoverageResult(covered=[], uncovered=[])` zurück
  (kein Fehler, keine Blockierung — der Check ist nicht anwendbar).
- Die Methode ist deterministisch: gleiche Eingaben → gleiche Ausgabe,
  kein Netzwerkaufruf, keine Seiteneffekte.
- Specs mit `status: implemented` werden von der Prüfung ausgenommen
  (kein rückwirkendes Enforcement).
