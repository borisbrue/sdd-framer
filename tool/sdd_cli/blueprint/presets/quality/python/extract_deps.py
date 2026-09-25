"""AST-Abhängigkeitsextraktor des sdd-Presets `python` → sdd-deps auf stdout (SPEC-0054 FR-14).

Aufruf: `python3 .sdd/quality/extract_deps.py <dateien…>` im Projektverzeichnis.

Kantenarten:
- import: Importe von Modulen **des Projekts** (externe Bibliotheken zählen für die
  Architektur nicht und werden ausgelassen); dynamische Importe als unaufgelöst.
- call:   Aufrufe über importierte Namen, voll qualifiziert (z. B. subprocess.run), mit
          statisch lesbaren String-Argumenten.
- write:  open(..., "w"/"a"/"x"), Path.write_text/write_bytes, os.replace, shutil.copy*/move;
          Ziel aus Literalen und Modulkonstanten, sonst unaufgelöst.
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

IGNORED_DIRS = {".git", ".sdd", ".venv", "venv", "node_modules", "__pycache__", "build", "dist"}
WRITE_METHODS = {"write_text", "write_bytes"}
WRITE_FUNCS = {"os.replace": 1, "os.rename": 1, "shutil.copy": 1, "shutil.copy2": 1,
               "shutil.copyfile": 1, "shutil.move": 1}


def _module_parts(rel: Path) -> tuple[Path, list[str]]:
    """(Quellwurzel, Modulteile) – die Wurzel liegt oberhalb des obersten Pakets."""
    teile = list(rel.with_suffix("").parts)
    verzeichnis = rel.parent
    while verzeichnis != Path(".") and (verzeichnis / "__init__.py").is_file():
        verzeichnis = verzeichnis.parent
    wurzel_teile = len(verzeichnis.parts) if verzeichnis != Path(".") else 0
    modul = teile[wurzel_teile:]
    if modul and modul[-1] == "__init__":
        modul = modul[:-1]
    return verzeichnis, modul


def _index() -> dict[str, str]:
    """Modulname → Datei für alle Python-Dateien des Projekts."""
    index = {}
    for pfad in Path(".").rglob("*.py"):
        if IGNORED_DIRS & set(pfad.parts):
            continue
        _, modul = _module_parts(pfad)
        if modul:
            index.setdefault(".".join(modul), pfad.as_posix())
    return index


class _Visitor(ast.NodeVisitor):
    def __init__(self, rel: str, modul: list[str], is_package: bool, index: dict[str, str]):
        self.rel, self.index = rel, index
        self.paket = modul if is_package else modul[:-1]
        self.alias: dict[str, str] = {}
        self.konstanten: dict[str, str] = {}
        self.edges: list[dict] = []

    def _edge(self, kind: str, target: str | None, symbol: str, node: ast.AST, **extra) -> None:
        kante = {"from": self.rel, "to": target, "kind": kind, "symbol": symbol,
                 "file": self.rel, "line": getattr(node, "lineno", 1), **extra}
        if target is None:
            kante["unresolved"] = True
        self.edges.append(kante)

    # ── Importe ──
    def _projekt_import(self, modul: str, symbol: str, node: ast.AST) -> None:
        if modul in self.index:
            self._edge("import", self.index[modul], symbol, node)

    def visit_Import(self, node: ast.Import) -> None:
        for a in node.names:
            self.alias[a.asname or a.name.split(".")[0]] = a.name if a.asname else a.name.split(".")[0]
            self._projekt_import(a.name, a.asname or a.name, node)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.level:
            basis = self.paket[: len(self.paket) - (node.level - 1)] if node.level > 1 else self.paket
            modul = ".".join([*basis, *(node.module.split(".") if node.module else [])])
        else:
            modul = node.module or ""
        for a in node.names:
            self.alias[a.asname or a.name] = f"{modul}.{a.name}" if modul else a.name
            unter = f"{modul}.{a.name}" if modul else a.name
            if unter in self.index:
                self._edge("import", self.index[unter], a.name, node)
            elif modul in self.index:
                self._edge("import", self.index[modul], a.name, node)
        self.generic_visit(node)

    # ── Aufrufe und Schreibzugriffe ──
    def _qualified(self, func: ast.AST) -> str | None:
        teile = []
        while isinstance(func, ast.Attribute):
            teile.append(func.attr)
            func = func.value
        if not isinstance(func, ast.Name):
            return None
        basis = self.alias.get(func.id)
        if basis is None:
            return func.id if not teile else None
        return ".".join([basis, *reversed(teile)])

    def _pfad(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.Name):
            return self.konstanten.get(node.id)
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Div)):
            links, rechts = self._pfad(node.left), self._pfad(node.right)
            if links is None or rechts is None:
                return None
            return f"{links.rstrip('/')}/{rechts.lstrip('/')}" if isinstance(node.op, ast.Div) \
                else links + rechts
        if isinstance(node, ast.Call) and self._qualified(node.func) == "pathlib.Path" and node.args:
            return self._pfad(node.args[0])
        return None

    @staticmethod
    def _norm(pfad: str | None) -> str | None:
        if pfad is None or pfad.startswith("/"):
            return None
        return pfad[2:] if pfad.startswith("./") else pfad

    def visit_Call(self, node: ast.Call) -> None:
        name = self._qualified(node.func)
        if name in ("__import__", "importlib.import_module"):
            ziel = self._pfad(node.args[0]) if node.args else None
            if ziel and ziel in self.index:
                self._edge("import", self.index[ziel], ziel, node)
            elif ziel is None:
                self._edge("import", None, name, node)
        elif name == "open":
            modus = node.args[1] if len(node.args) > 1 else next(
                (k.value for k in node.keywords if k.arg == "mode"), None)
            if isinstance(modus, ast.Constant) and set(str(modus.value)) & set("wax+"):
                ziel = self._norm(self._pfad(node.args[0])) if node.args else None
                self._edge("write", ziel, "open", node)
        elif name in WRITE_FUNCS and len(node.args) > WRITE_FUNCS[name]:
            self._edge("write", self._norm(self._pfad(node.args[WRITE_FUNCS[name]])), name, node)
        elif isinstance(node.func, ast.Attribute) and node.func.attr in WRITE_METHODS:
            ziel = self._norm(self._pfad(node.func.value))
            self._edge("write", ziel, f"pathlib.Path.{node.func.attr}", node)
        elif name and "." in name:
            self._edge("call", None, name, node, args=self._args(node))
        self.generic_visit(node)

    @staticmethod
    def _args(node: ast.Call) -> list[str]:
        werte = []
        for a in node.args:
            if isinstance(a, ast.Constant) and isinstance(a.value, str):
                werte.append(a.value)
            elif isinstance(a, (ast.List, ast.Tuple)):
                werte += [e.value for e in a.elts
                          if isinstance(e, ast.Constant) and isinstance(e.value, str)]
        return werte


def _konstanten(baum: ast.Module) -> dict[str, str]:
    werte = {}
    for stmt in baum.body:
        if isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Constant) \
                and isinstance(stmt.value.value, str):
            for ziel in stmt.targets:
                if isinstance(ziel, ast.Name):
                    werte[ziel.id] = stmt.value.value
    return werte


def main(argv: list[str]) -> int:
    index = _index()
    edges = []
    for arg in argv:
        rel = Path(arg)
        if rel.suffix != ".py" or not rel.is_file():
            continue
        try:
            baum = ast.parse(rel.read_text(encoding="utf-8"), filename=arg)
        except (SyntaxError, UnicodeDecodeError):
            continue
        _, modul = _module_parts(rel)
        v = _Visitor(rel.as_posix(), modul, rel.name == "__init__.py", index)
        v.konstanten = _konstanten(baum)
        v.visit(baum)
        edges += v.edges
    json.dump({"format": "sdd-deps", "version": 1, "tool": {"name": "extract_deps.py"},
               "kinds_provided": ["import", "call", "write"], "edges": edges}, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
