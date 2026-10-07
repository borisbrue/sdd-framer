# language: de
Funktionalität: Aufrufform des claude-cli-Providers
  Als Pipeline im keyfreien Betrieb
  möchte ich claude als reine Completion-Engine aufrufen
  um keinen Claude-Code-Overhead pro Aufruf zu bezahlen

  Szenario: Agent-Fähigkeiten sind abgeschaltet
    Wenn der Provider complete("Hallo") aufruft
    Dann ist die Argumentliste genau --print, --output-format json, --tools "", --setting-sources "", --strict-mcp-config, --system-prompt-file <datei>
    Und die Umgebung des Kindprozesses enthält CLAUDE_CODE_DISABLE_AUTO_MEMORY=1
    Und die übrige Umgebung ist unverändert

  Szenario: System-Prompt als echter System-Prompt
    Wenn der Provider complete("Hallo", system_prompt="Sei knapp.") aufruft
    Dann liest claude aus der Datei hinter --system-prompt-file genau "Sei knapp."
    Und die Datei hat beim Aufruf den Modus 0600
    Und claude liest über stdin genau "Hallo"
    Und die Datei existiert nach dem Aufruf nicht mehr

  Szenario: Ohne System-Prompt
    Wenn der Provider complete("Hallo") aufruft
    Dann ist die Datei hinter --system-prompt-file leer
    Und claude liest über stdin genau "Hallo"

  Szenario: Großer Prompt
    Angenommen ein Prompt mit 200.000 Zeichen
    Wenn der Provider ihn aufruft
    Dann liest claude ihn vollständig über stdin
    Und kein Argument enthält den Prompt

  Szenario: Großer System-Prompt
    Angenommen ein System-Prompt mit 200.000 Zeichen
    Wenn der Provider complete("Hallo", system_prompt=<dieser Text>) aufruft
    Dann liest claude ihn vollständig aus der Datei hinter --system-prompt-file
    Und kein Argument enthält den System-Prompt

  Szenario: Datei wird auch nach Timeout gelöscht
    Angenommen claude antwortet nicht innerhalb des Timeouts
    Wenn der Provider complete("Hallo", system_prompt="x", timeout=1) aufruft
    Dann wirft er RuntimeError mit "Timeout nach 1s"
    Und der claude-Prozess läuft nicht mehr
    Und die Datei hinter --system-prompt-file existiert nicht mehr

  Szenario: CLI scheitert ohne Envelope
    Angenommen claude endet mit Exit-Code 2, leerem stdout und stderr "error: unknown option '--tools'"
    Wenn der Provider complete("Hallo") aufruft
    Dann wirft er RuntimeError mit "Exit-Code 2" und "unknown option"
    Und die Datei hinter --system-prompt-file existiert nicht mehr

  Szenario: Umlaute und Sonderzeichen unter C-Locale
    Angenommen LC_ALL=C und LANG=C
    Und claude gibt den gelesenen Prompt als result zurück
    Wenn der Provider complete("Grüße – ✓", system_prompt="Läuft ✓") aufruft
    Dann liest claude über stdin genau "Grüße – ✓" und aus der Datei genau "Läuft ✓"
    Und der Provider gibt genau "Grüße – ✓" zurück

  Szenario: Fehlermeldung mit Umlauten unter C-Locale
    Angenommen LC_ALL=C und LANG=C
    Und claude endet mit Exit-Code 2, leerem stdout und stderr "Fehlä ✓"
    Wenn der Provider complete("Hallo") aufruft
    Dann wirft er RuntimeError mit "Exit-Code 2" und "Fehlä ✓"

  Szenario: Lange Fehlermeldung wird gekürzt
    Angenommen claude endet mit Exit-Code 3, leerem stdout und stderr aus 1.000 "#" gefolgt von 500 "B"
    Wenn der Provider complete("Hallo") aufruft
    Dann enthält der RuntimeError "Exit-Code 3" und die 500 "B" und kein "#"

  Szenario: CLI scheitert mit JSON ohne result
    Angenommen claude endet mit Exit-Code 1 und gibt {"type":"result","is_error":true} aus
    Wenn der Provider complete("Hallo") aufruft
    Dann wirft er RuntimeError mit "Exit-Code 1"

  Szenario: CLI scheitert mit Envelope
    Angenommen claude endet mit Exit-Code 1 und liefert ein Envelope mit result "Fehlertext"
    Wenn der Provider complete("Hallo") aufruft
    Dann gibt er "Fehlertext" zurück
