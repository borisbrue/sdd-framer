Feature: Verweise, Config-Aufräumen und sdd spec deprecate
  Als Nutzer von sdd-framer
  möchte ich, dass abgelöste Befehle auf ihren Ersatz verweisen, ohne etwas auszuführen
  um alte Aufrufe in Skripten sofort zu bemerken, ohne Nebenwirkungen im Repo

  Scenario Outline: Abgelöster Befehl verweist auf den Ersatz
    When ich "<aufruf>" ausführe
    Then ist der Exit-Code 1
    And die Ausgabe nennt "<ersatz>"
    And es wird kein LLM aufgerufen und kein Git-Befehl ausgeführt

    Examples:
      | aufruf                          | ersatz            |
      | sdd distribute SPEC-0900        | sdd pipeline run  |
      | sdd distribute SPEC-0900 --dry-run | sdd pipeline run |

  Scenario: Verweise erscheinen nicht in der Hilfe
    When ich "sdd --help" ausführe
    Then wird "distribute" nicht gelistet

  Scenario: Entfernte Module sind weg
    Given der Code unter tool/sdd_cli
    Then gibt es sub_agent.py, local_agent.py, autopilot.py, dist_orchestrator.py, review_pipeline.py, llm_pool.py, dag_command.py und dag_event.py nicht mehr
    And kein Modul setzt ANTHROPIC_API_KEY oder ANTHROPIC_BASE_URL

  Scenario: Config-Aufräumen beim Upgrade
    Given config.yaml enthält die Blöcke llm_pool, local_agent und autopilot
    When ich "sdd upgrade" ausführe
    Then sind die drei Blöcke auskommentiert und ihr Inhalt bleibt als Kommentar erhalten
    And die Ausgabe meldet jeden auskommentierten Block
    And die übrigen Einträge von config.yaml sind unverändert

  Scenario: Upgrade ohne alte Blöcke
    Given config.yaml enthält keinen der Blöcke llm_pool, local_agent und autopilot
    When ich "sdd upgrade" ausführe
    Then bleibt config.yaml unverändert

  Scenario: Spec wird abgelöst
    Given SPEC-0900 hat den Status implemented
    When ich "sdd spec deprecate SPEC-0900 --reason 'abgelöst' --replaced-by SPEC-0901" ausführe
    Then hat SPEC-0900 den Status deprecated
    And das Frontmatter nennt den Grund und SPEC-0901 als Nachfolger
    And das Audit-Log enthält die Statusänderung

  Scenario: Deprecate mit abhängigen Specs
    Given SPEC-0902 hängt von SPEC-0900 ab und ist nicht deprecated
    When ich "sdd spec deprecate SPEC-0900 --reason 'abgelöst'" ausführe
    Then hat SPEC-0900 den Status deprecated
    And die Ausgabe warnt vor der abhängigen SPEC-0902

  Scenario: Deprecate einer unbekannten Spec
    When ich "sdd spec deprecate SPEC-0999 --reason 'x'" ausführe
    Then ist der Exit-Code 2
