"""SPEC-0054 FR-03, CON-0195/CON-0196: FR-Erfüllung aus ausgeführten Tests."""
from __future__ import annotations

import json

import pytest

from sdd_cli.quality.parsers import TestCase
from sdd_cli.quality.requirements import evaluate_requirements
from sdd_cli.quality.settings import QualitySettings


def _spec(root, frs, fr_test_map=None, contracts=()):
    fm = ["id: SPEC-0900", "title: T", "status: approved", f"contracts: {list(contracts)}"]
    if fr_test_map:
        fm.append("fr_test_map: " + json.dumps(fr_test_map))
    body = "\n".join(f"- **{fr}:** Text" for fr in frs)
    (root / ".sdd/specs").mkdir(parents=True, exist_ok=True)
    (root / ".sdd/specs/SPEC-0900-t.md").write_text(
        "---\n" + "\n".join(fm) + "\n---\n\n## 4. Funktionale Anforderungen\n\n" + body + "\n")


def _case(name, status, frs=(), file=None):
    return TestCase(name, "c", status, tuple(frs), file)


def _eval(root, cases, **kw):
    return evaluate_requirements(root, "SPEC-0900", cases, fr_marker="property",
                                 settings=kw.pop("settings", QualitySettings()), **kw)


@pytest.mark.parametrize(("stati", "erwartet"), [
    (["passed", "passed"], "erfüllt"), (["passed", "failed"], "teilweise"),
    (["failed", "error"], "fehlt"), ([], "fehlt"), (["skipped", "skipped"], "fehlt"),
    (["passed", "skipped"], "erfüllt")])
def test_status(tmp_path, stati, erwartet):
    _spec(tmp_path, ["FR-07"])
    r = _eval(tmp_path, [_case(f"t{i}", s, ["FR-07"]) for i, s in enumerate(stati)])
    assert r.frs[0].status == erwartet


def test_anteil_und_reihenfolge(tmp_path):
    _spec(tmp_path, ["FR-01", "FR-02", "FR-03", "FR-04"])
    r = _eval(tmp_path, [_case("a", "passed", ["FR-01"]), _case("b", "passed", ["FR-02"]),
                         _case("c", "passed", ["FR-03"]), _case("d", "failed", ["FR-03"])])
    assert [f.id for f in r.frs] == ["FR-01", "FR-02", "FR-03", "FR-04"]
    assert r.node.score() == pytest.approx(0.5)


def test_ausgefallene_testsonde(tmp_path):
    _spec(tmp_path, ["FR-01", "FR-02"])
    r = _eval(tmp_path, None, na_reason="Befehl nicht gefunden")
    assert {f.status for f in r.frs} == {"unbekannt"}
    assert r.node.score() is None and "Befehl nicht gefunden" in r.node.na_reason()


def test_fr_test_map_mit_testnamen_und_not_run(tmp_path):
    _spec(tmp_path, ["FR-01"], fr_test_map={"FR-01": ["test_x", "test_fehlt"]})
    r = _eval(tmp_path, [_case("test_x", "passed")])
    tests = {t["name"]: t for t in r.frs[0].tests}
    assert tests["test_x"] == {"name": "test_x", "status": "passed", "source": "fr_test_map"}
    assert tests["test_fehlt"]["status"] == "not_run"
    assert r.frs[0].status == "teilweise"


def test_fr_test_map_mit_tst_id_ueber_artefakt(tmp_path):
    _spec(tmp_path, ["FR-01"], fr_test_map={"FR-01": ["TST-0901"]})
    (tmp_path / ".sdd/tests/unit").mkdir(parents=True)
    (tmp_path / ".sdd/tests/unit/TST-0901-x.md").write_text(
        '---\nid: TST-0901\nartifact: "tests/unit/test_x.py"\n---\n')
    r = _eval(tmp_path, [_case("t1", "passed", file="tests/unit/test_x.py"),
                         _case("t2", "failed", file="tests/unit/anders.py")])
    assert [t["name"] for t in r.frs[0].tests] == ["t1"]
    assert r.frs[0].status == "erfüllt"


def test_task_fr_ids(tmp_path):
    _spec(tmp_path, ["FR-01"])
    (tmp_path / ".sdd/tasks").mkdir(parents=True)
    (tmp_path / ".sdd/tasks/SPEC-0900.json").write_text(json.dumps([
        {"title": "x", "fr_ids": ["FR-01"], "test_file": "tests/unit/test_y.py"}]))
    r = _eval(tmp_path, [_case("t", "failed", file="tests/unit/test_y.py")])
    assert r.frs[0].tests == [{"name": "t", "status": "failed", "source": "task_fr_ids"}]


def test_marker_quelle_nach_fr_marker(tmp_path):
    _spec(tmp_path, ["FR-01"])
    r = evaluate_requirements(tmp_path, "SPEC-0900", [_case("t_FR-01", "passed", ["FR-01"])],
                              fr_marker="name", settings=QualitySettings())
    assert r.frs[0].tests[0]["source"] == "junit_name"


def test_spec_ohne_fr(tmp_path):
    _spec(tmp_path, [])
    r = _eval(tmp_path, [])
    assert r.frs == [] and r.node.score() is None and r.node.na_reason() == "Spec ohne FR"
