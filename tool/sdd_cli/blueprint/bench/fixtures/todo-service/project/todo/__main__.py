"""Einstieg für `python -m todo` (Schicht `entry`, verdrahtet CLI und Persistenz)."""
import sys

from todo.cli import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
