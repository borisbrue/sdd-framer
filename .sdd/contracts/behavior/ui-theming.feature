Feature: UI Theme-Auswahl und Persistenz
  Als User möchte ich zwischen drei Themes wählen können,
  damit die Oberfläche meinen Vorlieben entspricht.

  Background:
    Given die Anwendung ist im Browser geöffnet

  Scenario: Standardtheme für neue User ist Dark
    Given localStorage enthält keinen Eintrag für "sdd-theme"
    When die Anwendung lädt
    Then ist "dark" das aktive Theme
    And das <html>-Element hat das Attribut data-theme="dark"

  Scenario: User öffnet die Einstellungsseite
    When der User auf den Einstellungen-Button klickt
    Then ist die Einstellungsseite sichtbar
    And alle drei Themes "dark", "light" und "cyberpunk" sind aufgelistet
    And das aktuell aktive Theme ist visuell hervorgehoben

  Scenario: User wechselt auf das Light-Theme
    Given das aktive Theme ist "dark"
    When der User die Einstellungsseite öffnet
    And das Theme "light" auswählt
    Then ist "light" das aktive Theme
    And das <html>-Element hat das Attribut data-theme="light"
    And localStorage["sdd-theme"] ist "light"

  Scenario: User wechselt auf das Cyberpunk-Theme
    Given das aktive Theme ist "dark"
    When der User das Theme "cyberpunk" auswählt
    Then ist "cyberpunk" das aktive Theme
    And das <html>-Element hat das Attribut data-theme="cyberpunk"

  Scenario: Theme überlebt einen Browser-Reload
    Given der User hat das Theme "cyberpunk" ausgewählt
    When der User die Seite neu lädt
    Then ist "cyberpunk" das aktive Theme ohne erneute Auswahl

  Scenario: Immer genau ein Theme aktiv
    Given das aktive Theme ist "light"
    When der User das Theme "cyberpunk" auswählt
    Then ist "cyberpunk" aktiv
    And "light" ist nicht mehr aktiv
    And "dark" ist nicht aktiv
