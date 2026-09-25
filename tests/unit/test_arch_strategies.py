"""SPEC-0054 FR-05, CON-0194 INV-03..INV-09: je Regelart eine Strategie."""
from __future__ import annotations

from sdd_cli.quality.arch.rules import Rule
from sdd_cli.quality.arch.strategies import STRATEGIES, required_kind
from sdd_cli.quality.parsers import DepsGraph, Edge

LAYERS = {"web": ["web/**"], "cli": ["cli/**"], "llm": ["llm/**"]}


def _edge(src, tgt, kind="import", symbol="S", args=(), line=1):
    return Edge(src, tgt, kind, symbol, src, line, tuple(args), tgt is None)


def _run(kind, params, edges):
    rule = Rule(id="ARCH-01", adr="ADR-0001", kind=kind, severity="error", params=params)
    g = DepsGraph(frozenset({"import", "call", "write"}), edges)
    return [(v.file, v.symbol) for v in STRATEGIES[kind].evaluate(rule, g, LAYERS)]


def test_benoetigte_kantenarten():
    assert required_kind("forbidden_dependency") == "import"
    assert required_kind("allowed_dependencies") == "import"
    assert required_kind("forbidden_call") == "call"
    assert required_kind("write_ownership") == "write"


def test_forbidden_dependency_schichten_und_pfade():
    edges = [_edge("web/a.py", "cli/writer.py", symbol="w"), _edge("web/a.py", "llm/p.py",
                                                                   symbol="p"),
             _edge("cli/b.py", "llm/p.py", symbol="ok"), _edge("web/a.py", None, symbol="dyn")]
    assert _run("forbidden_dependency", {"from": "web", "to_layers": ["llm"]}, edges) == [
        ("web/a.py", "p")]
    assert _run("forbidden_dependency", {"from": ["web"], "to_paths": ["cli/writer.py"]},
                edges) == [("web/a.py", "w")]


def test_allowed_dependencies():
    edges = [_edge("web/a.py", "cli/c.py", symbol="ok1"),
             _edge("cli/c.py", "cli/d.py", symbol="gleich"),
             _edge("cli/c.py", "web/a.py", symbol="rueck"),
             _edge("llm/p.py", "cli/c.py", symbol="ohne"),
             _edge("scripts/x.py", "web/a.py", symbol="ohne_schicht")]
    assert _run("allowed_dependencies", {"graph": {"web": ["cli"], "cli": ["llm"]}}, edges) == [
        ("cli/c.py", "rueck"), ("llm/p.py", "ohne")]


def test_forbidden_call():
    edges = [_edge("cli/a.py", None, "call", "subprocess.run", ["claude", "--print"]),
             _edge("cli/b.py", None, "call", "subprocess.run", ["git"]),
             _edge("llm/claude.py", None, "call", "subprocess.Popen", ["claude"]),
             _edge("cli/c.py", None, "call", "subprocess.os.system", ["claude"]),
             _edge("web/d.py", None, "call", "subprocess.run", ["claude"])]
    params = {"in": ["cli", "llm"], "calls": ["subprocess.*"], "args_match": "^claude$",
              "except": ["llm/claude.py"]}
    assert _run("forbidden_call", params, edges) == [("cli/a.py", "subprocess.run")]


def test_forbidden_call_ohne_args_match():
    edges = [_edge("cli/a.py", None, "call", "os.system")]
    assert _run("forbidden_call", {"in": "cli", "calls": ["os.system"]}, edges) == [
        ("cli/a.py", "os.system")]


def test_write_ownership():
    edges = [_edge("web/a.py", ".sdd/specs/S.md", "write", "pathlib.Path.write_text"),
             _edge("cli/b.py", ".sdd/specs/S.md", "write", "pathlib.Path.write_text"),
             _edge("web/a.py", "build/o.txt", "write", "open")]
    assert _run("write_ownership", {"paths": [".sdd/specs/**"], "owners": ["cli"]}, edges) == [
        ("web/a.py", "pathlib.Path.write_text")]
