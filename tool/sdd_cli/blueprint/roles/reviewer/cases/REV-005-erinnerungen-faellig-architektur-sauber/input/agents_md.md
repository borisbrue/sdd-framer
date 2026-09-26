# AGENTS.md

## Architektur (Ports & Adapters)
```
reminders/cli.py        Einstieg, argparse, einzige Stelle mit Ausgaben (print/stderr)
reminders/domain/       reine Logik: Modelle, Regeln, Protokolle (Ports)
reminders/adapters/     Ein-/Ausgabe: JSON-Datei, Systemuhr
```

## Regeln
- `reminders/domain/` macht keine Ein-/Ausgabe und importiert nichts aus `reminders.adapters` oder `reminders.cli`.
- Die Domäne ruft nie `datetime.now()` auf; die aktuelle Zeit kommt über das Protokoll `Clock` als Parameter. Adapter dürfen die Systemuhr lesen.
- Alle Zeitpunkte sind zeitzonenbewusst (UTC).
- `print` nur in `reminders/cli.py`; sonst `logging`.
- Fehler der Adapter werden als `StoreError` gemeldet und in `cli.py` in Exit-Code 2 übersetzt.
