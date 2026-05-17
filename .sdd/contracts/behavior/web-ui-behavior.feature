# language: de
Funktionalität: SDD Web UI – Kernverhalten
  Als Entwickler
  möchte ich Specs, Contracts und Tests über eine Browser-Oberfläche verwalten
  um ohne CLI-Wissen produktiv zu sein

  Hintergrund:
    Angenommen der SDD-Server läuft auf http://localhost:8000
    Und das SDD-Projekt enthält mindestens eine Spec

  # ─────────────────────────────────────────────
  # Sidebar
  # ─────────────────────────────────────────────

  Szenario: Projektliste wird geladen
    Wenn der Nutzer http://localhost:8000 öffnet
    Dann zeigt die Sidebar mindestens einen Projekteintrag
    Und jeder Projekteintrag zeigt das Autonomy-Level-Badge

  Szenario: Spec-Liste aufklappen
    Angenommen die Sidebar zeigt ein Projekt "Demo"
    Wenn der Nutzer auf "Demo" klickt
    Dann erscheint die Liste der Specs dieses Projekts unterhalb des Eintrags

  Szenario: Neue Spec anlegen (Schnellzugriff)
    Wenn der Nutzer auf "+ Spec" klickt
    Dann öffnet sich das SpecForm-Modal
    Wenn der Nutzer Titel "Meine Spec" eingibt und auf "Speichern" klickt
    Dann erscheint "Meine Spec" in der Seitenleiste
    Und die neue Spec hat den Status "draft"

  Szenario: Neues Projekt anlegen (Schnellzugriff)
    Wenn der Nutzer auf "+ Projekt" klickt
    Dann öffnet sich das ProjectForm-Modal
    Wenn der Nutzer Name "Neues Projekt" und Owner "Boris" eingibt und speichert
    Dann erscheint "Neues Projekt" in der Projektliste

  # ─────────────────────────────────────────────
  # SpecDetail
  # ─────────────────────────────────────────────

  Szenario: Spec-Detail anzeigen
    Angenommen die Spec "SPEC-0001" existiert mit Titel "Meine Spec"
    Wenn der Nutzer auf "SPEC-0001" in der Sidebar klickt
    Dann zeigt der Hauptbereich Frontmatter (ID, Status, Owner, Priority)
    Und den Markdown-Body der Spec
    Und die Liste der verknüpften Contracts
    Und die Liste der verknüpften Tests

  Szenario: Spec im Editor öffnen
    Angenommen die Spec-Detail-Ansicht für "SPEC-0001" ist offen
    Wenn der Nutzer auf "Im Editor öffnen" klickt
    Dann wird POST /api/open mit dem absoluten Dateipfad aufgerufen
    Und VS Code öffnet die Datei

  # ─────────────────────────────────────────────
  # AI-Panel
  # ─────────────────────────────────────────────

  Szenario: Spec mit KI generieren
    Wenn der Nutzer im AiPanel Titel "Cache-Invalidierung" und Beschreibung eingibt
    Und auf "Spec generieren" klickt
    Dann sendet die UI POST /api/ai/generate-spec
    Und zeigt das KI-Ergebnis im Textbereich an
    Und zeigt den Token-Verbrauch der Operation

  Szenario: Spec mit KI verbessern
    Angenommen die Spec-Detail-Ansicht für "SPEC-0001" ist offen
    Wenn der Nutzer im AiPanel eine Verbesserungsanweisung eingibt
    Und auf "Spec verbessern" klickt
    Dann sendet die UI POST /api/ai/improve-spec mit spec_id und Anweisung
    Und zeigt das überarbeitete Spec-Ergebnis an

  Szenario: KI-Nutzungskosten einsehen
    Wenn der Nutzer die AiUsageView öffnet
    Dann zeigt die Seite Gesamtkosten in USD
    Und Anzahl Aufrufe nach Operation aufgeschlüsselt
    Und Anzahl Input- und Output-Token

  # ─────────────────────────────────────────────
  # Validierung & Traceability
  # ─────────────────────────────────────────────

  Szenario: Validierung durchführen – alles OK
    Angenommen alle Specs haben gültige Frontmatter und Contracts
    Wenn der Nutzer in der StatusBar auf "Validieren" klickt
    Dann sendet die UI POST /api/validate
    Und zeigt "✓ Keine Fehler" in der StatusBar

  Szenario: Validierung durchführen – Fehler vorhanden
    Angenommen eine Spec fehlt das Pflichtfeld "owner"
    Wenn der Nutzer auf "Validieren" klickt
    Dann zeigt die UI eine Fehlerliste mit Dateiname und Fehlermeldung
    Und die StatusBar signalisiert den Fehlerzustand

  Szenario: Traceability-Matrix aktualisieren
    Wenn der Nutzer auf "Traceability" klickt
    Dann sendet die UI POST /api/trace
    Und zeigt eine Erfolgsmeldung mit dem Pfad zur erzeugten Datei

  Szenario: Maintenance-Sweep auslösen
    Wenn der Nutzer auf "Maintenance" klickt
    Dann sendet die UI GET /api/maintenance
    Und zeigt die Anzahl veralteter Specs und Drift-Issues
    Und listet jedes Issue mit Severity, Datei und empfohlener Aktion auf

  # ─────────────────────────────────────────────
  # Autonomy Level
  # ─────────────────────────────────────────────

  Szenario: Autonomy Level setzen
    Angenommen das Projekt "Demo" hat aktuell Level 2
    Wenn der Nutzer das Autonomy-Level-Badge auf "Level 3" ändert
    Dann sendet die UI PATCH /api/projects/demo/level mit body {"level": 3}
    Und das Badge in der Sidebar zeigt sofort "Level 3 – AI-reviewed"

  Szenariogrundriss: Autonomy-Level-Badge Darstellung
    Angenommen das Projekt hat autonomy_level <level>
    Dann zeigt das Badge den Text "<label>"

    Beispiele:
      | level | label              |
      | 1     | Level 1 – Manuell  |
      | 2     | Level 2 – AI-assisted |
      | 3     | Level 3 – AI-reviewed |
      | 3.5   | Level 3.5 – AI-gated  |
      | 4     | Level 4 – Fully autonomous |

  # ─────────────────────────────────────────────
  # Navigation & Theme
  # ─────────────────────────────────────────────

  Szenario: Breadcrumb-Navigation – Zurück
    Angenommen der Nutzer hat Spec "SPEC-0001" geöffnet
    Wenn der Nutzer auf "Zurück" klickt
    Dann navigiert die UI zur vorherigen Ansicht ohne Seitenneuladen

  Szenario: Dark-Mode aktivieren
    Angenommen der Nutzer ist in den Einstellungen
    Wenn der Nutzer den Dark/Light-Theme-Umschalter betätigt
    Dann wechselt die gesamte UI das Farbschema sofort ohne Neuladen
    Und die Einstellung bleibt nach einem Browser-Refresh erhalten
