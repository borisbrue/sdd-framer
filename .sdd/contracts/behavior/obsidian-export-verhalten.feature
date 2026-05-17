Feature: Obsidian Vault Export

  Background:
    Given das SDD-CLI ist installiert
    And ein SDD-Projekt mit SPEC-0001 und CON-0001 existiert
    And der Vault-Pfad ist in config.yaml konfiguriert als "~/TestVault"

  # ── Dateistruktur ────────────────────────────────────────────────────────────

  Scenario: Export legt korrekte Unterordner an
    When der Entwickler "sdd obsidian export" ausführt
    Then existiert SDD/specs/ im Vault
    And existiert SDD/contracts/ im Vault
    And existiert SDD/tests/ im Vault
    And existiert SDD/adrs/ im Vault

  Scenario: Export erzeugt Dateien mit korrektem Namen
    Given SPEC-0001 hat den Slug "user-login"
    When der Entwickler "sdd obsidian export" ausführt
    Then existiert SDD/specs/SPEC-0001-user-login.md im Vault

  Scenario: Export erzeugt Index-Datei
    When der Entwickler "sdd obsidian export" ausführt
    Then existiert SDD/index.md im Vault
    And SDD/index.md enthält Wiki-Links auf alle exportierten Artefakte

  # ── Wiki-Links ───────────────────────────────────────────────────────────────

  Scenario: ID-Referenzen werden in Wiki-Links umgewandelt
    Given SPEC-0001 enthält im Body "CON-0001 beschreibt das Login-Verhalten"
    And CON-0001 hat den Slug "login"
    When der Entwickler "sdd obsidian export" ausführt
    Then enthält die exportierte SPEC-0001-Datei "[[CON-0001-login]]"
    And enthält nicht "CON-0001 beschreibt" (rohe ID bleibt nicht übrig)

  Scenario: auto_wiki_links=false deaktiviert Wiki-Link-Konvertierung
    Given "auto_wiki_links: false" in config.yaml
    And SPEC-0001 enthält im Body "CON-0001 beschreibt das Login-Verhalten"
    When der Entwickler "sdd obsidian export" ausführt
    Then enthält die exportierte SPEC-0001-Datei "CON-0001 beschreibt" (unveränderter Text)
    And enthält nicht "[[CON-0001"

  # ── Überschreiben-Logik ──────────────────────────────────────────────────────

  Scenario: Neuere Projekt-Version überschreibt ältere Vault-Datei
    Given SPEC-0001 im Vault hat "updated: 2026-05-01"
    And SPEC-0001 im Projekt hat "updated: 2026-05-14"
    When der Entwickler "sdd obsidian export" ausführt
    Then wird die Vault-Datei überschrieben

  Scenario: Gleich alte oder neuere Vault-Datei wird nicht überschrieben
    Given SPEC-0001 im Vault hat "updated: 2026-05-14"
    And SPEC-0001 im Projekt hat "updated: 2026-05-14"
    When der Entwickler "sdd obsidian export" ausführt
    Then wird die Vault-Datei nicht überschrieben

  # ── Dry-Run ──────────────────────────────────────────────────────────────────

  Scenario: Dry-Run zeigt geplante Aktionen ohne zu schreiben
    When der Entwickler "sdd obsidian export --dry-run" ausführt
    Then enthält der Output die geplanten Dateipfade
    And keine Datei wurde im Vault geschrieben

  # ── Fehlerbehandlung ─────────────────────────────────────────────────────────

  Scenario: Fehlender Vault-Pfad ohne --vault-Flag
    Given kein "obsidian.vault_path" in config.yaml
    And kein --vault Flag übergeben
    When "sdd obsidian export" ausgeführt wird
    Then enthält der Output "obsidian.vault_path nicht konfiguriert"
    And der Exit-Code ist 2

  Scenario: Vault-Pfad existiert nicht
    Given vault_path zeigt auf nicht-existentes Verzeichnis "/nonexistent/vault"
    When "sdd obsidian export" ausgeführt wird
    Then enthält der Output den fehlenden Pfad
    And der Exit-Code ist 2

  Scenario: Vault-Pfad ist Unterverzeichnis des SDD-Projekts
    Given vault_path ist ein Unterverzeichnis des SDD-Projekts
    When "sdd obsidian export" ausgeführt wird
    Then wird eine ValueError ausgelöst
    And der Exit-Code ist 2

  Scenario: Idempotenz – zweiter Export ohne Änderungen
    Given "sdd obsidian export" wurde bereits einmal ausgeführt
    When "sdd obsidian export" erneut ausgeführt wird
    Then sind alle Vault-Dateien identisch zum ersten Durchlauf
