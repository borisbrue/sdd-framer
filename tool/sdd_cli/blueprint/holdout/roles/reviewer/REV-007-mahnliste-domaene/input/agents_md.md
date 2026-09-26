# AGENTS.md (vereinskasse)

## Architektur (Ports & Adapters)

- `kasse/domain/` – Fachlogik. **Importiert weder `sqlite3` noch Module aus `kasse/adapters/`
  und macht keine Datei- oder Datenbankzugriffe.** Daten kommen über die Ports in
  `kasse/domain/ports.py` herein (`MitgliederRepository`, `BeitragRepository`, `Clock`).
- `kasse/adapters/` – SQLite-Implementierungen der Ports (`sqlite_repo.py`), Schema in
  `kasse/adapters/schema.sql`.
- `kasse/cli.py` – verdrahtet Adapter und Domäne.
- Domänentests arbeiten mit In-Memory-Fakes der Ports, nicht mit einer Datenbank.

## Ports (Auszug aus kasse/domain/ports.py)

```python
class BeitragRepository(Protocol):
    def offene(self) -> list[OffenerBeitrag]: ...   # mitglied_id, name, betrag: Decimal, faellig: date

class Clock(Protocol):
    def today(self) -> date: ...
```
