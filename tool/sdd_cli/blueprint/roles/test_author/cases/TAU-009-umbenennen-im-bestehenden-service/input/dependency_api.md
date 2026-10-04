### todo/domain.py (T01 Todo-Fachobjekte)

```
MAX_TITLE = 200

class ValidationError(ValueError):
    """Eingabe verletzt eine Fachregel."""

class TodoNotFoundError(LookupError):
    """Es gibt kein Todo mit dieser ID."""

@dataclass(frozen=True)
class Todo:
    """Ein Todo; unveränderlich, Änderungen erzeugen ein neues Objekt."""
    id: int
    title: str
    done: bool = False

def clean_title(title: str) -> str:
    """Titel ohne Leerraum an den Rändern; leer oder länger als MAX_TITLE ist ein Fehler."""
```

### todo/repository.py (T02 Ablage im Speicher)

```
class InMemoryRepository:
    """Hält Todos nach ID; `save` legt an oder ersetzt."""
    def __init__(self) -> None:
        ...
    def next_id(self) -> int:
        """Nächste freie ID, beginnend bei 1."""
    def save(self, todo: Todo) -> None:
        """Legt das Todo an oder ersetzt das mit gleicher ID."""
    def get(self, todo_id: int) -> Todo | None:
        """Das Todo mit dieser ID oder None."""
    def todos(self) -> list[Todo]:
        """Alle Todos nach ID sortiert."""
```
