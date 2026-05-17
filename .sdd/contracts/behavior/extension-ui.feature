Feature: SDD VS Code Extension – UI-Verhalten

  Scenario: TreeView zeigt alle Specs
    Given ein SDD-Projekt ist geöffnet mit SPEC-0001 und SPEC-0002
    When die SDD-Sidebar geladen wird
    Then zeigt die TreeView "Specs (2)"
    And SPEC-0001 und SPEC-0002 sind als Einträge sichtbar

  Scenario: Spec-Node ist aufklappbar und zeigt Contracts und Tests
    Given SPEC-0001 hat contracts: [CON-0001] und tests: [TST-0001]
    When der Nutzer SPEC-0001 in der TreeView aufklappt
    Then werden CON-0001 und TST-0001 als Kinder angezeigt

  Scenario: Code Lens zeigt Contract- und Test-Anzahl
    Given specs/SPEC-0001-user-login.md ist geöffnet
    Then erscheint über der ersten Überschrift "3 contracts · 4 tests · ✓"

  Scenario: Fehlende Verknüpfung zeigt Lücken-Warnung
    Given specs/SPEC-0002-*.md hat contracts: []
    When der Nutzer die Spec öffnet
    Then zeigt Code Lens "0 contracts · 0 tests · ⚠ 2 Lücken"

  Scenario: Diagnostics nach Speichern
    Given eine Spec ohne Contract wird gespeichert
    Then erscheint ein Fehler im Problems-Panel
    And die Zeilennummer ist 1
