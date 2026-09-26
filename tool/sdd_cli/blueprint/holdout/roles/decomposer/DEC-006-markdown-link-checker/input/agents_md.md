# AGENTS.md (linkwart)

- Paket `linkwart/`, Einstieg `linkwart/cli.py` (argparse). Kernlogik ohne I/O in eigenen Modulen,
  Dateizugriff nur in `linkwart/scan.py`.
- Tests unter `tests/`, `unittest`, Aufruf `python3 -m unittest discover -s tests -t .`.
- Keine Netzwerkzugriffe, keine Fremdpakete.
