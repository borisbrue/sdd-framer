"""Python-Extraktor: öffentliche Klassen, Attribute, Methoden und Funktionen (SPEC-0065 FR-03).

Öffentlich ist, was nicht mit `_` beginnt; `__init__` gehört dazu, weil es die Konstruktion
beschreibt. Je Definition Dekoratoren, Signatur und die erste Docstring-Zeile, nie der Rumpf.
Werte von Konstanten und Attributen nur, wenn sie kurz sind.
"""
from __future__ import annotations

import ast

from ..signatures import ExtractionError, register

MAX_WERT = 60  # Zeichen; längere Werte erscheinen als `...`

_Definition = ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef


def _oeffentlich(name: str) -> bool:
    return not name.startswith("_") or name == "__init__"


def _rumpf(knoten: _Definition, einzug: str) -> list[str]:
    text = ast.get_docstring(knoten)
    erste = text.strip().splitlines()[0] if text and text.strip() else ""
    return [f'{einzug}    """{erste}"""'] if erste else [f"{einzug}    ..."]


def _dekoratoren(knoten: _Definition, einzug: str) -> list[str]:
    return [f"{einzug}@{ast.unparse(d)}" for d in knoten.decorator_list]


def _funktion(knoten: ast.FunctionDef | ast.AsyncFunctionDef, einzug: str) -> list[str]:
    asynchron = "async " if isinstance(knoten, ast.AsyncFunctionDef) else ""
    rueckgabe = f" -> {ast.unparse(knoten.returns)}" if knoten.returns else ""
    kopf = f"{einzug}{asynchron}def {knoten.name}({ast.unparse(knoten.args)}){rueckgabe}:"
    return [*_dekoratoren(knoten, einzug), kopf, *_rumpf(knoten, einzug)]


def _wert(knoten: ast.expr | None) -> str:
    if knoten is None:
        return ""
    text = ast.unparse(knoten)
    return f" = {text}" if len(text) <= MAX_WERT and "\n" not in text else " = ..."


def _attribut(knoten: ast.stmt, einzug: str) -> list[str]:
    if isinstance(knoten, ast.AnnAssign) and isinstance(knoten.target, ast.Name) \
            and _oeffentlich(knoten.target.id):
        typ = ast.unparse(knoten.annotation)
        return [f"{einzug}{knoten.target.id}: {typ}{_wert(knoten.value)}"]
    if isinstance(knoten, ast.Assign):
        namen = [z.id for z in knoten.targets if isinstance(z, ast.Name) and _oeffentlich(z.id)]
        return [f"{einzug}{n}{_wert(knoten.value)}" for n in namen]
    return []


def _klasse(knoten: ast.ClassDef) -> list[str]:
    basen = [ast.unparse(b) for b in knoten.bases] + [ast.unparse(k) for k in knoten.keywords]
    klammer = "(" + ", ".join(basen) + ")" if basen else ""
    zeilen = [*_dekoratoren(knoten, ""), f"class {knoten.name}{klammer}:"]
    doc = ast.get_docstring(knoten)
    if doc and doc.strip():
        zeilen.append(f'    """{doc.strip().splitlines()[0]}"""')
    for kind in knoten.body:
        if isinstance(kind, (ast.FunctionDef, ast.AsyncFunctionDef)) and _oeffentlich(kind.name):
            zeilen += _funktion(kind, "    ")
        else:
            zeilen += _attribut(kind, "    ")
    return zeilen if len(zeilen) > 1 + len(knoten.decorator_list) else [*zeilen, "    ..."]


def extract(text: str) -> list[str]:
    try:
        baum = ast.parse(text)
    except (SyntaxError, ValueError) as exc:
        raise ExtractionError(str(exc)) from exc
    bloecke: list[list[str]] = []
    for knoten in baum.body:
        if isinstance(knoten, ast.ClassDef) and _oeffentlich(knoten.name):
            bloecke.append(_klasse(knoten))
        elif isinstance(knoten, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                and _oeffentlich(knoten.name):
            bloecke.append(_funktion(knoten, ""))
        elif (attribute := _attribut(knoten, "")):
            bloecke.append(attribute)
    return [z for i, b in enumerate(bloecke) for z in ([""] if i else []) + b]


register(".py", extract)
