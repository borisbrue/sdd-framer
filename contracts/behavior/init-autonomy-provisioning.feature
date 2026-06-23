Feature: sdd init Autonomie-Provisioning
  sdd init rüstet ein Projekt mit dem Guardrail aus; Bypass nur opt-in und nur lokal. (SPEC-0051)

  Scenario: init installiert den Guardrail-Hook-Wrapper
    Given ein Zielprojekt ohne .claude/hooks/
    When "sdd init" ausgeführt wird
    Then existiert .claude/hooks/autonomous-guardrail.sh (ausführbar)
    And .claude/settings.json enthält einen PreToolUse/Bash-Hook auf dieses Script

  Scenario: Hook-Merge ist idempotent
    Given ein Projekt, das bereits per sdd init den Guardrail-Hook hat
    When "sdd init" erneut ausgeführt wird
    Then existiert genau ein Guardrail-PreToolUse-Hook (kein Duplikat)
    And die bestehende permissions.allow-Liste bleibt unverändert erhalten

  Scenario: ohne --autonomous kein Bypass
    Given ein frisches Zielprojekt
    When "sdd init" ohne --autonomous ausgeführt wird
    Then enthält .claude/settings.json kein permissions.defaultMode
    And es wird keine .claude/settings.local.json mit defaultMode angelegt

  Scenario: --autonomous setzt Bypass nur lokal
    Given ein frisches Zielprojekt
    When "sdd init --autonomous" ausgeführt wird
    Then enthält .claude/settings.local.json "permissions.defaultMode" = "bypassPermissions"
    And .gitignore enthält einen Eintrag für settings.local.json
    And .claude/settings.json (committed) enthält weiterhin kein defaultMode
