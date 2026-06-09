---
id: CON-0154
title: TypeAwareTestChecker — Integration-Test-Pflicht für webui/api-Specs
type: behavior
format: markdown
spec: SPEC-0041
version: 0.1.0
status: approved
tests:
- TST-0179
---
`TypeAwareTestChecker` meldet `severity: error` für jede Spec mit einem
der Tags `webui`, `frontend` oder `api`, die keinen verknüpften Test mit
`stufe: contract` oder `stufe: integration` hat.

**Garantien**

- Die Prüfung basiert ausschließlich auf den Frontmatter-Feldern `tags`
  der Spec und `stufe` der verknüpften Test-Dateien unter `.sdd/tests/`.
- Ein Test gilt als qualifizierend wenn seine Markdown-Datei unter
  `.sdd/tests/contract/` oder `.sdd/tests/integration/` liegt ODER
  sein Frontmatter `stufe: contract` bzw. `stufe: integration` enthält.
- Specs ohne die genannten Tags erzeugen kein Issue (nur streng typen-
  spezifisch).
- Der Check ist unabhängig vom Inhalt der Tests — er prüft Typ und
  Vorhandensein, nicht Qualität (Qualität = SPEC-0028).
