Feature: Rollenkontext beim Erweitern
  Als Pipeline
  möchte ich Test-Autor und Implementer den bestehenden Code und die Schnittstellen ihrer Abhängigkeiten zeigen
  damit sie erweitern statt erfinden

  Scenario: Test-Autor sieht bestehenden Code
    Given eine Task erweitert die vorhandene Datei src/service.py aus ihren allowed_paths
    When der Test-Autor aufgerufen wird
    Then enthält sein Prompt den Abschnitt current_files mit dem Inhalt von src/service.py
    And die Testdatei der Task erscheint dort nicht

  Scenario: Schnittstellen einer erledigten Abhängigkeit
    Given T02 hängt von T01 ab, T01 ist erledigt und hat src/storage.py mit class Store und def save(self) -> None geschrieben
    When der Implementer von T02 aufgerufen wird
    Then nennt dependency_api src/storage.py mit class Store und save(self) -> None
    And kein Rumpf aus src/storage.py erscheint

  Scenario: Abhängigkeit noch offen
    Given T02 hängt von T01 ab und T01 ist nicht erledigt
    When der Test-Autor von T02 aufgerufen wird
    Then ist dependency_api leer

  Scenario: Datei ohne Extraktor
    Given eine erledigte Abhängigkeit hat die Datei config/app.toml geschrieben
    When dependency_api gebildet wird
    Then nennt sie config/app.toml nur mit Pfad und Hinweis

  Scenario: Kürzung nach Budget
    Given die Dateien einer Task überschreiten das Budget von current_files
    When der Test-Autor aufgerufen wird
    Then endet current_files mit einem Kürzungshinweis

  Scenario: Prüf-Task als test
    Given eine Spec mit einer Anforderung, die nur bestehendes Verhalten absichert
    When der Decomposer zerlegt
    Then hat die Task dafür den Typ test
