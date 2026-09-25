"""SPEC-0054 FR-07, CON-0198: Baseline."""
from __future__ import annotations

import json

import pytest

from sdd_cli.quality.arch.baseline import Baseline, BaselineError
from sdd_cli.quality.arch.evaluator import Violation


def _v(file="w/a.py", symbol="C", severity="error"):
    return Violation(rule="ARCH-01", adr="ADR-0001", file=file, line=3, symbol=symbol,
                     severity=severity)


def test_herabstufen_und_veraltet(tmp_path):
    b = Baseline([{"rule": "ARCH-01", "file": "w/a.py", "symbol": "C", "reason": "alt"},
                  {"rule": "ARCH-01", "file": "w/z.py", "symbol": "Z", "reason": "alt"}])
    vs = b.apply([_v(), _v(symbol="D")])
    assert (vs[0].severity, vs[0].baselined) == ("warn", True)
    assert (vs[1].severity, vs[1].baselined) == ("error", False)
    assert b.stale == 1


def test_laden_und_schemafehler(tmp_path):
    (tmp_path / ".sdd/quality").mkdir(parents=True)
    pfad = tmp_path / ".sdd/quality/arch-baseline.json"
    assert Baseline.load(tmp_path).entries == []
    pfad.write_text(json.dumps({"version": 1, "entries": [{"rule": "ARCH-01"}]}))
    with pytest.raises(BaselineError):
        Baseline.load(tmp_path)


def test_fortschreiben_erhaelt_gruende(tmp_path):
    b = Baseline([{"rule": "ARCH-01", "file": "w/a.py", "symbol": "C", "reason": "Altlast"}])
    neu = b.merged_with([_v(), _v(file="w/b.py")])
    assert [(e["file"], e["reason"]) for e in neu.entries] == [("w/a.py", "Altlast"),
                                                               ("w/b.py", "TODO")]
    neu.write(tmp_path)
    daten = json.loads((tmp_path / ".sdd/quality/arch-baseline.json").read_text())
    assert daten["version"] == 1 and len(daten["entries"]) == 2
