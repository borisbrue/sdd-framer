"""`python -m todo` (SPEC-0002 FR-06, SPEC-0003 FR-09)."""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from collections.abc import Callable

from todo.domain import StorageError, Todo, TodoNotFoundError, ValidationError
from todo.service import TodoService

ServiceFactory = Callable[[str], TodoService]


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="todo", description="Aufgaben verwalten")
    p.add_argument("--file", default="todo.json", help="JSON-Datei (Default: todo.json)")
    sub = p.add_subparsers(dest="befehl", required=True)
    add = sub.add_parser("add", help="Aufgabe anlegen")
    add.add_argument("title")
    add.add_argument("--tag", action="append", default=[])
    add.add_argument("--due")
    lst = sub.add_parser("list", help="Aufgaben auflisten")
    lst.add_argument("--tag")
    status = lst.add_mutually_exclusive_group()
    status.add_argument("--open", action="store_true")
    status.add_argument("--done", action="store_true")
    lst.add_argument("--search")
    for name in ("done", "reopen", "delete"):
        sub.add_parser(name).add_argument("id", type=int)
    exp = sub.add_parser("export", help="Aufgaben exportieren")
    exp.add_argument("--format", choices=["json", "csv"], default="json")
    return p


def _datum(text: str | None) -> dt.date | None:
    if text is None:
        return None
    try:
        return dt.date.fromisoformat(text)
    except ValueError:
        raise ValidationError(f"Ungültiges Datum {text!r} (erwartet JJJJ-MM-TT).") from None


def _zeile(t: Todo) -> str:
    zeile = f"[{'x' if t.done else ' '}] #{t.id} {t.title}"
    if t.due:
        zeile += f" due:{t.due.isoformat()}"
    if t.tags:
        zeile += " tags:" + ",".join(t.tags)
    return zeile


def _run(args: argparse.Namespace, open_service: ServiceFactory) -> str:
    if args.befehl == "add":
        due = _datum(args.due)
        todo = open_service(args.file).add(args.title, tags=args.tag, due=due)
        return f"#{todo.id} {todo.title}\n"
    svc = open_service(args.file)
    if args.befehl == "list":
        done = True if args.done else False if args.open else None
        return "".join(_zeile(t) + "\n" for t in
                       svc.list_todos(done=done, tag=args.tag, text=args.search))
    if args.befehl == "done":
        svc.complete(args.id)
    elif args.befehl == "reopen":
        svc.reopen(args.id)
    elif args.befehl == "delete":
        svc.delete(args.id)
    elif args.befehl == "export":
        return svc.export_json() if args.format == "json" else svc.export_csv()
    return ""


def main(argv: list[str] | None = None, open_service: ServiceFactory | None = None) -> int:
    """Führt einen Befehl aus und gibt den Exit-Code zurück (0 Erfolg, 1 Fehler, 2 Aufruf)."""
    args = _parser().parse_args(argv)
    if open_service is None:
        print("todo: kein Speicher verdrahtet (python -m todo verwenden)", file=sys.stderr)
        return 2
    try:
        ausgabe = _run(args, open_service)
    except (ValidationError, TodoNotFoundError, StorageError) as exc:
        print(f"todo: {exc}", file=sys.stderr)
        return 1
    sys.stdout.write(ausgabe)
    return 0
