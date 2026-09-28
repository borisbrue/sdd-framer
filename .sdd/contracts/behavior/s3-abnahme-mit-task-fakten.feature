Feature: S3-Abnahme mit Task-Fakten
  Als Supervisor
  möchte ich an der Abnahme die Tasks des Runs mit ihren FRs sehen
  um reopen gezielt auf die richtigen Tasks anzuwenden

  Scenario: Schnappschuss bei der Freigabe
    Given ein Run, dessen Zerlegung drei Tasks vorschlägt
    When der Supervisor an S1 approve entscheidet
    Then steht im Run-Verzeichnis tasks.json mit diesen drei Tasks und der request_id der S1-Anfrage

  Scenario: Abnahme nennt Tasks und ihre FRs
    Given ein Run mit den Tasks T01 (FR-01), T02 (FR-02) und T03 (FR-03), alle erledigt
    When die Pipeline die Abnahme S3 anfragt
    Then enthält facts.tasks drei Einträge mit id, title, fr_ids, test_file, state und attempts
    And facts.frs nennt für FR-03 die Tasks ["T03"]
    And die Anfrage erfüllt CON-0202

  Scenario: FR ohne Task und Task ohne FR
    Given FR-04 wird von keiner Task abgedeckt und T04 hat keine fr_ids
    When die Pipeline die Abnahme S3 anfragt
    Then nennt facts.frs für FR-04 die Tasks []
    And erscheint T04 in facts.tasks mit fr_ids []

  Scenario: reopen mit Task-IDs aus den Fakten
    Given die S3-Anfrage nennt für FR-03 die Tasks ["T03"]
    When der Supervisor reopen mit task_ids ["T03"] entscheidet
    Then ist die Entscheidung gültig und T03 steht wieder auf red
    And die nächste S3-Anfrage zeigt für T03 den neuen Stand

  Scenario: Schnappschuss fehlt
    Given tasks.json fehlt im Run-Verzeichnis
    When die Pipeline die Abnahme erreicht
    Then hält der Run mit einem Grund, der tasks.json nennt
    And es gibt keine offene S3-Anfrage

  Scenario: Neue Zerlegung ersetzt den Schnappschuss
    Given ein Run mit freigegebenem tasks.json
    When der Supervisor an S2 redecompose entscheidet und die neue Zerlegung an S1 freigibt
    Then enthält tasks.json die neuen Tasks
