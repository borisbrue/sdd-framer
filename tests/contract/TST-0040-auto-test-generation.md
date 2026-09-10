---
id: TST-0040
title: "Auto Test Generation – Contract-Format-Verhalten"
level: contract
spec: SPEC-0014
contract: CON-0028
status: implemented
framework: pytest
artifact: "tests/contract/test_con_0028.py"
tags: [test-generation, gherkin, openapi, json-schema]
---

# Test: Auto Test Generation (CON-0028)

> **Level:** contract · **Spec:** SPEC-0014 · **Contract:** CON-0028

## Was wird geprüft?

Korrekte Generierung von Pytest-Stubs aus verschiedenen Contract-Formaten, Header-Invariante, manuelle Zusatz-Tests bleiben bei Re-Run erhalten.

## Vorbedingungen

- `tool/sdd_cli/test_generator.py` implementiert
- Temporäres Verzeichnis mit Contract-Fixtures

## Ablauf

1. Gherkin-Contract → pytest-Funktionen pro Scenario
2. OpenAPI-Contract → `import httpx`-Stub pro Endpunkt
3. JSON-Schema-Contract → valide + invalide Instanz Tests
4. Generierter Code ist syntaktisch valide (ast.parse)
5. Alle Scenarios aus Feature-Datei sind abgedeckt
6. Error-Scenarios enthalten passenden Kommentar
7. Re-Run eines bestehenden Tests → manuelle Funktionen bleiben erhalten
8. Syntaxfehler in Generierung → Phase 6 blockiert

## Verknüpfung mit Contract

- [x] INV-04: Header `# AUTO-GENERATED from <CON-ID> via sdd test generate`
- [x] INV-05: Manuell hinzugefügte Tests bleiben bei Re-Run erhalten
- [x] INV-07: Syntaxfehler → `success=False`, Phase blockiert
