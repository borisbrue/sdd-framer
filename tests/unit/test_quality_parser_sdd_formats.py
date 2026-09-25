"""SPEC-0054 FR-02, CON-0193: Parser für sdd-deps, sdd-metrics und sdd-findings."""
from __future__ import annotations

import json

import pytest

from sdd_cli.quality.parsers import ParseError, parse_output


def _parse(tmp_path, fmt, daten):
    datei = tmp_path / "out.json"
    datei.write_text(json.dumps(daten), encoding="utf-8")
    return parse_output(fmt, datei, tmp_path)


def test_deps(tmp_path):
    g = _parse(tmp_path, "sdd-deps", {"format": "sdd-deps", "version": 1,
                                       "kinds_provided": ["import", "call"], "edges": [
        {"from": "a.py", "to": "b.py", "kind": "import", "symbol": "B", "file": "a.py", "line": 2},
        {"from": "a.py", "to": None, "kind": "call", "symbol": "x.run", "args": ["c"],
         "file": "a.py", "line": 5, "unresolved": True}]})
    assert g.kinds == frozenset({"import", "call"})
    assert g.edges[0].source == "a.py" and g.edges[0].target == "b.py"
    assert g.edges[1].args == ("c",) and g.edges[1].unresolved


def test_metrics(tmp_path):
    r = _parse(tmp_path, "sdd-metrics", {"format": "sdd-metrics", "version": 1, "metrics": [
        {"name": "complexity_max", "value": 12}, {"name": "c", "value": 1, "scope": "a.py"}]})
    assert [(m.name, m.value, m.scope) for m in r.metrics] == [
        ("complexity_max", 12, "project"), ("c", 1, "a.py")]


def test_findings(tmp_path):
    r = _parse(tmp_path, "sdd-findings", {"format": "sdd-findings", "version": 1, "findings": [
        {"rule": "R", "message": "m", "file": "a.go", "line": 4, "severity": "error"}]})
    assert [(f.rule, f.file, f.line, f.severity) for f in r.findings] == [("R", "a.go", 4, "error")]


def test_schemaverletzung(tmp_path):
    with pytest.raises(ParseError):
        _parse(tmp_path, "sdd-findings", {"format": "sdd-findings", "version": 1})


def test_formatfeld_passt_nicht_zur_sonde(tmp_path):
    with pytest.raises(ParseError):
        _parse(tmp_path, "sdd-metrics", {"format": "sdd-findings", "version": 1, "findings": []})


def test_kein_json(tmp_path):
    datei = tmp_path / "x"
    datei.write_text("nope", encoding="utf-8")
    with pytest.raises(ParseError):
        parse_output("sdd-deps", datei, tmp_path)
