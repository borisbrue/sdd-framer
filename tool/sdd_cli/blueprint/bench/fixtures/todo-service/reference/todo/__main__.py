"""Einstieg für `python -m todo` (Schicht `entry`, verdrahtet CLI und Persistenz)."""
import sys

from todo.cli import main
from todo.persistence import JsonFileRepository
from todo.service import TodoService


def open_service(path: str) -> TodoService:
    return TodoService(JsonFileRepository(path))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], open_service=open_service))
