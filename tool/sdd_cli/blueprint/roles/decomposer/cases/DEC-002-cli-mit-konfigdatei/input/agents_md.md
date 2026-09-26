# AGENTS.md (Auszug)

- Python 3.12, nur Standardbibliothek. Paket `logsum/`, Einstieg `logsum/cli.py` (`main(argv)`
  gibt den Exit-Code zurück, ruft nie selbst `sys.exit`).
- Parsen und Zählen in `logsum/counter.py`, Konfiguration in `logsum/settings.py`,
  Ausgabeformate in `logsum/output.py`. `cli.py` verdrahtet nur.
- Tests: `tests/test_<modul>.py` mit `unittest`; Befehl `python3 -m unittest discover -s tests -t .`
- Tasks bleiben klein: höchstens `medium`, lieber ein Task mehr.
