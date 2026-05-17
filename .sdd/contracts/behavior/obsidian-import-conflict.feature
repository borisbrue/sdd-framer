Feature: Obsidian Vault Import und Conflict-Erkennung

  Background:
    Given das SDD-CLI ist installiert
    And ein SDD-Projekt mit SPEC-0001 existiert
    And SPEC-0001 wurde zuvor in den Vault exportiert

  # ── Normaler Import ──────────────────────────────────────────────────────────

  Scenario: Import nach manuellem Edit ohne Conflict
    Given SPEC-0001 wurde im Vault bearbeitet (Vault-Datei neuer als Projekt-Datei)
    And das Projekt-SPEC-0001 wurde seit dem Export nicht verändert
    When der Entwickler "sdd obsidian import" ausführt
    Then wird specs/SPEC-0001-user-login.md mit dem Vault-Inhalt überschrieben
    And das "updated:"-Feld enthält das heutige Datum

  Scenario: Wiki-Links werden beim Import zurückkonvertiert
    Given die Vault-Datei enthält "[[CON-0001-login]]"
    When der Entwickler "sdd obsidian import" ausführt
    Then enthält die importierte Projekt-Datei "CON-0001" (rohe ID)
    And enthält nicht "[[CON-0001-login]]"

  # ── Conflict-Erkennung ───────────────────────────────────────────────────────

  Scenario: Conflict bei beidseitiger Änderung
    Given SPEC-0001 wurde exportiert
    And SPEC-0001 wurde sowohl im Vault als auch im Projekt verändert
    When der Entwickler "sdd obsidian import" ausführt
    Then wird SPEC-0001 nicht überschrieben
    And .sdd/obsidian-conflicts.yaml enthält SPEC-0001 als Conflict-Eintrag
    And der Exit-Code ist 1

  Scenario: Conflict-Eintrag enthält Pflichtfelder
    Given ein Conflict für SPEC-0001 wurde erkannt
    When .sdd/obsidian-conflicts.yaml gelesen wird
    Then enthält der Eintrag die Felder "id", "vault_path", "project_path", "detected_at"

  # ── Filterung ────────────────────────────────────────────────────────────────

  Scenario: Datei mit unbekannter ID wird übersprungen
    Given eine Vault-Datei hat "id: UNKNOWN-9999" im Frontmatter
    When der Entwickler "sdd obsidian import" ausführt
    Then wird die Datei nicht importiert
    And der Output enthält eine Warnung

  Scenario: Datei mit ungültigem YAML-Frontmatter wird übersprungen
    Given eine Vault-Datei hat ungültiges YAML-Frontmatter
    When der Entwickler "sdd obsidian import" ausführt
    Then wird die Datei übersprungen
    And .sdd/obsidian-warnings.log enthält einen Eintrag

  Scenario: ID stimmt nicht mit Dateinamen überein
    Given eine Vault-Datei heißt "SPEC-0001-user-login.md" aber hat "id: SPEC-0002"
    When der Entwickler "sdd obsidian import" ausführt
    Then wird die Datei nicht importiert
    And .sdd/obsidian-warnings.log enthält einen Eintrag mit dem Dateinamen

  # ── Path-Traversal-Schutz ────────────────────────────────────────────────────

  Scenario: Datei außerhalb vault_path wird abgewiesen
    Given eine Vault-Datei enthält einen Pfad-Verweis auf "../../etc/passwd"
    When der Entwickler "sdd obsidian import" ausführt
    Then wird eine ValueError ausgelöst
    And keine Datei außerhalb vault_path wird gelesen oder geschrieben

  # ── Watch-Modus ──────────────────────────────────────────────────────────────

  Scenario: Watch-Modus importiert Dateiänderung automatisch
    Given "sdd obsidian watch" läuft mit Intervall 1 Sekunde
    When eine Vault-Datei geändert wird
    Then wird die Änderung innerhalb von 2 Sekunden ins Projekt importiert

  Scenario: Watch stoppt sauber auf SIGINT
    Given "sdd obsidian watch" läuft
    When SIGINT gesendet wird
    Then beendet sich der Prozess sauber ohne Exception
