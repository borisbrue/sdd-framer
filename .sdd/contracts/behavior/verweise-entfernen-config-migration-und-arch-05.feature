Feature: Verweise, Entfernen, Config-Migration und ARCH-05
  Als Nutzer von sdd-framer
  möchte ich, dass die alten Ausführungspfade auf die Pipeline verweisen und meine Config übernommen wird
  um ohne Datenverlust auf den einen Pfad umzusteigen

  Scenario Outline: Abgelöster Befehl verweist auf die Pipeline
    When ich "<aufruf>" ausführe
    Then ist der Exit-Code 1
    And die Ausgabe nennt "<ersatz>"
    And es wird kein LLM aufgerufen und keine Datei geändert

    Examples:
      | aufruf                         | ersatz                                   |
      | sdd task-route SPEC-0900 T01   | sdd pipeline run SPEC-0900 --task T01    |
      | sdd task-exec SPEC-0900 T01    | sdd pipeline run SPEC-0900 --task T01    |
      | sdd task-loop SPEC-0900        | sdd pipeline run SPEC-0900               |
      | sdd orchestrate SPEC-0900      | sdd pipeline run SPEC-0900 --auto        |

  Scenario: Verweise erscheinen nicht in der Hilfe
    When ich "sdd --help" ausführe
    Then werden task-route, task-exec, task-loop und orchestrate nicht gelistet

  Scenario: Entfernte Module sind weg
    Given der Code unter tool/sdd_cli
    Then gibt es task_routing/, orchestrator.py und llm_probe.py nicht mehr
    And kein Modul definiert oder importiert CodeGenProvider oder get_code_gen_provider

  Scenario: Config-Migration mit Routing
    Given config.yaml enthält task_routing.enabled true mit complexity_threshold 50
    And llm.local_llm mit provider openai-compat, model "m" und base_url "http://h/v1"
    When ich "sdd upgrade" ausführe
    Then enthält config.yaml llm.profiles.lokal mit provider openai-compat, model "m" und base_url "http://h/v1"
    And llm.roles.implementer.by_complexity ordnet low und medium dem Profil lokal zu, high nicht
    And task_routing und llm.local_llm sind mit "# [SPEC-0062] " auskommentiert
    And die Ausgabe meldet Profil, Zuordnung und beide auskommentierten Blöcke

  Scenario: Routing war abgeschaltet
    Given config.yaml enthält task_routing.enabled false und llm.local_llm
    When ich "sdd upgrade" ausführe
    Then enthält config.yaml llm.profiles.lokal
    And llm.roles.implementer hat kein by_complexity
    And task_routing und llm.local_llm sind auskommentiert

  Scenario: Routing ohne lokales Modell
    Given config.yaml enthält task_routing, aber kein llm.local_llm
    When ich "sdd upgrade" ausführe
    Then ist nur task_routing auskommentiert und die Ausgabe nennt den Grund

  Scenario: Bestehende Rollen werden nicht überschrieben
    Given config.yaml enthält task_routing, llm.local_llm und bereits llm.profiles.lokal
    When ich "sdd upgrade" ausführe
    Then bleibt config.yaml unverändert
    And die Ausgabe nennt den Konflikt mit llm.profiles.lokal

  Scenario: Migration ist idempotent
    Given "sdd upgrade" hat die Config bereits migriert
    When ich "sdd upgrade" erneut ausführe
    Then bleibt config.yaml unverändert

  Scenario: Abgelöste Artefakte
    Then hat SPEC-0045 den Status deprecated mit Nachfolger SPEC-0061
    And CON-0171, CON-0172, CON-0173, CON-0174 und CON-0012 haben den Status deprecated

  Scenario: ARCH-05 schützt die Interna der Pipeline
    Given ein Modul in tool/sdd_cli/web importiert sdd_cli.pipeline.mediator
    When ich "sdd arch check" ausführe
    Then meldet die Prüfung einen Verstoß gegen ARCH-05 mit ADR-0006

  Scenario: Repository ist regelkonform
    When ich "sdd arch check" im Repository ausführe
    Then gibt es keine neuen Verstöße
    And die Baseline enthält keinen Eintrag mit fixed_by SPEC-0061 oder SPEC-0062
