# SPEC-0018: Ablage für Anhänge

## 1. Zweck
Nutzer laden Anhänge zu Tickets hoch und wieder herunter. Die Namen der Anhänge kommen beim Herunterladen aus der URL.

## 4. Funktionale Anforderungen

- **FR-01:** `save(data, suffix)` legt einen Anhang unter einem zufälligen Namen in `base_dir` ab und liefert den Namen.
- **FR-02:** Anhänge sind höchstens 10 MB groß (Prüfung im HTTP-Handler, nicht in der Ablage).
- **FR-03:** `open_attachment(name)` liefert den Inhalt des Anhangs. Existiert er nicht oder zeigt `name` auf eine Datei außerhalb von `base_dir`, wird `AttachmentNotFound` geworfen; es werden nie Dateien außerhalb von `base_dir` gelesen.
