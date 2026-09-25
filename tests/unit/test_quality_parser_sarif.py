"""SPEC-0054 FR-02, CON-0193 INV-08: SARIF-Parser und Gleichwertigkeit mit sdd-findings."""
from __future__ import annotations

import json

import pytest

from sdd_cli.quality.parsers import ParseError, parse_output


def _sarif(results, **run):
    return json.dumps({"version": "2.1.0", "runs": [{"tool": {"driver": {"name": "t"}},
                                                      "results": results, **run}]})


def _loc(uri, line=None, **extra):
    region = {"startLine": line} if line else {}
    return {"locations": [{"physicalLocation": {"artifactLocation": {"uri": uri, **extra},
                                                "region": region}}]}


def _parse(tmp_path, text):
    datei = tmp_path / "out.sarif"
    datei.write_text(text, encoding="utf-8")
    return parse_output("sarif", datei, tmp_path)


def test_abbildung_nach_contract(tmp_path):
    ergebnis = _parse(tmp_path, _sarif([
        {"ruleId": "E1", "message": {"text": "m1"}, "level": "error", **_loc("src/a.py", 3)},
        {"rule": {"id": "R2"}, "message": {"text": "m2"}, **_loc("src/a.py")},
        {"message": {"text": "m3"}, "level": "none", **_loc(f"file://{tmp_path}/src/b.py", 9)},
        {"ruleId": "N", "message": {"text": "m4"}, "level": "note", **_loc("src/a.py", 1)},
    ]))
    f = ergebnis.findings
    assert [(x.rule, x.file, x.line, x.severity) for x in f] == [
        ("E1", "src/a.py", 3, "error"), ("R2", "src/a.py", 1, "warning"),
        ("unknown", "src/b.py", 9, "note"), ("N", "src/a.py", 1, "note")]
    assert f[0].message == "m1"


def test_uri_base_id_wird_aufgeloest(tmp_path):
    ergebnis = _parse(tmp_path, _sarif(
        [{"ruleId": "E", "message": {"text": "m"}, **_loc("a.py", 1, uriBaseId="SRC")}],
        originalUriBaseIds={"SRC": {"uri": "src/"}}))
    assert ergebnis.findings[0].file == "src/a.py"


def test_befunde_ausserhalb_der_wurzel_werden_verworfen_und_gezaehlt(tmp_path):
    ergebnis = _parse(tmp_path, _sarif(
        [{"ruleId": "E", "message": {"text": "m"}, **_loc("file:///anderswo/x.py", 1)}]))
    assert ergebnis.findings == []
    assert ergebnis.discarded == 1


@pytest.mark.parametrize("text", ["{", "{}", '{"runs": 3}'])
def test_ungueltig(tmp_path, text):
    with pytest.raises(ParseError):
        _parse(tmp_path, text)
