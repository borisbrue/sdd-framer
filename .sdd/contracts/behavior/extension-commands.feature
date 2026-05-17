Feature: SDD VS Code Extension – Befehle

  Background:
    Given ein Workspace mit gültigem .sdd/config.yaml ist geöffnet
    And die sdd-CLI ist installiert und erreichbar

  Scenario: Neue Spec anlegen
    When der Nutzer "SDD: New Spec" wählt und "Checkout Flow" eingibt
    Then existiert specs/SPEC-XXXX-checkout-flow.md mit korrektem Frontmatter
    And die TreeView zeigt den neuen Eintrag

  Scenario: Neuen Contract anlegen
    When der Nutzer "SDD: New Contract" wählt, SPEC-0001 und Format "openapi" angibt
    Then existiert contracts/api/CON-XXXX-*.md
    And der Hinweis enthält die neue Contract-ID

  Scenario: Validierung schlägt fehl
    Given specs/SPEC-0002-*.md hat contracts: []
    When der Nutzer "SDD: Validate" wählt
    Then erscheint mindestens ein Fehler im Problems-Panel
    And die Fehlermeldung enthält "require_contract_per_spec"

  Scenario: Validierung erfolgreich
    Given alle Specs haben mindestens einen Contract und einen Test
    When der Nutzer "SDD: Validate" wählt
    Then erscheint "Alles in Ordnung" in der VS Code Benachrichtigung

  Scenario: Traceability-Matrix aktualisieren
    When der Nutzer "SDD: Update Trace Matrix" wählt
    Then wird docs/traceability.md neu geschrieben
    And eine Erfolgsmeldung wird angezeigt
