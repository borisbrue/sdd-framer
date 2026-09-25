"""SPEC-0054 FR-03, CON-0197 INV-05/05a/05b: sdd test run mit Testsonde."""
from __future__ import annotations

import json

import pytest
import yaml

from sdd_cli import test_runner
from sdd_cli.config import load_config
from sdd_cli.init import init_project

JUNIT = ('<testsuite><testcase classname="tests.unit.test_x" name="t1" file="tests/unit/test_x.py">'
         '<properties><property name="fr" value="FR-01"/></properties></testcase>'
         '<testcase classname="tests.unit.test_x" name="t2" file="tests/unit/test_x.py">{fail}'
         '</testcase></testsuite>')


@pytest.fixture()
def projekt(tmp_path):
    init_project(tmp_path, title="P")
    (tmp_path / ".sdd/specs/SPEC-0900-t.md").write_text(
        "---\nid: SPEC-0900\ntitle: T\nstatus: approved\ntests: [TST-9001, TST-9002]\n---\n")
    (tmp_path / ".sdd/tests/unit").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".sdd/tests/unit/TST-9001-x.md").write_text(
        '---\nid: TST-9001\nartifact: "tests/unit/test_x.py"\n---\n')
    (tmp_path / ".sdd/tests/unit/TST-9002-y.md").write_text(
        '---\nid: TST-9002\nartifact: "tests/unit/test_y.py"\n---\n')
    return tmp_path


def _sonde(root, fail=""):
    (root / "j.xml").write_text(JUNIT.format(fail=fail))
    (root / ".sdd/quality.yaml").write_text(yaml.safe_dump({"version": 1, "probes": {
        "tests": {"command": "cp j.xml {out}", "format": "junit", "role": "tests",
                  "fr_marker": "property"}}}))


def test_ohne_quality_yaml_unveraendert(projekt):
    report = test_runner.run(load_config(projekt), "SPEC-0900")
    daten = report.to_json()
    assert "testcases" not in daten and "junit" not in daten and "git_sha" not in daten
    assert report.runner != "probe:tests"


def test_mit_testsonde(projekt):
    _sonde(projekt)
    report = test_runner.run(load_config(projekt), "SPEC-0900")
    assert report.runner == "probe:tests" and report.exit_code == 0
    assert [(t.test_id, t.status) for t in report.tests] == [("TST-9001", "passed"),
                                                              ("TST-9002", "missing")]
    daten = json.loads(sorted((projekt / ".sdd/test-runs").glob("SPEC-0900-*.json"))[-1]
                       .read_text())
    assert daten["testcases"][0] == {"name": "t1", "classname": "tests.unit.test_x",
                                     "status": "passed", "frs": ["FR-01"]}
    assert (projekt / daten["junit"]).is_file() and daten["junit"].endswith(".junit.xml")
    assert "git_sha" in daten


def test_fehlschlag_ergibt_exit_1(projekt):
    _sonde(projekt, fail="<failure/>")
    report = test_runner.run(load_config(projekt), "SPEC-0900")
    assert report.exit_code == 1
    assert report.tests[0].status == "failed"


def test_ausgefallene_sonde_ist_runtime_error(projekt):
    _sonde(projekt)
    daten = yaml.safe_load((projekt / ".sdd/quality.yaml").read_text())
    daten["probes"]["tests"]["command"] = "gibt-es-nicht-4711 > {out}"
    (projekt / ".sdd/quality.yaml").write_text(yaml.safe_dump(daten))
    with pytest.raises(RuntimeError, match="Befehl nicht gefunden"):
        test_runner.run(load_config(projekt), "SPEC-0900")


def test_latest_testcases_nach_git_sha(projekt):
    _sonde(projekt)
    test_runner.run(load_config(projekt), "SPEC-0900")
    treffer = test_runner.latest_probe_run(load_config(projekt), "SPEC-0900", sha=None)
    assert treffer is not None and treffer[0][0].name == "t1"
    assert test_runner.latest_probe_run(load_config(projekt), "SPEC-0900", sha="abc") is None
