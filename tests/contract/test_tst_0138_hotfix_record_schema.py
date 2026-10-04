"""TST-0138 – CON-0119: Hotfix-Record-Schema (#132).

Spec: SPEC-0031 · Contract: CON-0119
Bisher schrieb `sdd hotfix start` `commit: null` und `finalize` den Kurzhash; beides verletzt
INV-01/INV-04. Die Schema-Datei fehlte, der Contract war nie gegen den Code geprüft.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from sdd_cli import hotfix
from sdd_cli.hotfix import _read_hf, finalize, list_hotfixes, short_commit, start

REPO = Path(__file__).resolve().parents[2]
SCHEMA = REPO / ".sdd/contracts/data/hotfix-record-schema.schema.json"
HASH = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"


@pytest.fixture(scope="module")
def pruefer() -> Draft202012Validator:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _record(**felder) -> dict:
    return {"id": "HF-0001", "description": "Falscher Defaultwert", "status": "open",
            "created": "2026-05-30", "commit": "", **felder}


def test_artifact_aus_dem_contract_existiert():
    text = next((REPO / ".sdd/contracts/data").glob("CON-0119-*.md")).read_text(encoding="utf-8")
    assert f'artifact: "{SCHEMA.relative_to(REPO)}"' in text and SCHEMA.is_file()


@pytest.mark.parametrize("record", [
    _record(),
    _record(status="done", commit=HASH),
    _record(status="aborted"),
    _record(created="2026-05-30T10:10:19Z"),
])
def test_gueltige_records(pruefer, record):
    assert list(pruefer.iter_errors(record)) == []


@pytest.mark.parametrize("record,inv", [
    ({"id": "HF-0001", "status": "open", "commit": ""}, "INV-01 Pflichtfelder"),
    (_record(commit=None), "INV-01 kein null"),
    (_record(status="fixed"), "INV-02 Status"),
    (_record(id="HF-1"), "INV-03 ID-Format"),
    (_record(commit=HASH), "INV-04 offen mit Hash"),
    (_record(status="done", commit=""), "INV-04 done ohne Hash"),
    (_record(status="done", commit="a1b2c3d"), "INV-04 Kurzhash"),
    (_record(extra="x"), "INV-05 zusätzliche Felder"),
])
def test_ungueltige_records(pruefer, record, inv):
    assert list(pruefer.iter_errors(record)), inv


def test_start_schreibt_gueltigen_offenen_record(tmp_path, pruefer):
    (tmp_path / ".sdd").mkdir()
    hf_id = start(tmp_path, "Ziffernhash")
    daten = _read_hf(tmp_path / ".sdd/hotfixes" / f"{hf_id}.md")
    assert daten["commit"] == ""
    assert list(pruefer.iter_errors(daten)) == []


def _git_repo(root: Path) -> None:
    for befehl in (["init", "-q"], ["config", "user.email", "t@example.org"],
                   ["config", "user.name", "Test"], ["commit", "-q", "--allow-empty", "-m", "a"]):
        subprocess.run(["git", *befehl], cwd=root, check=True, capture_output=True)


def test_finalize_schreibt_vollen_hash(tmp_path, monkeypatch, pruefer):
    _git_repo(tmp_path)
    (tmp_path / ".sdd").mkdir()
    hf_id = start(tmp_path, "Fix")
    (tmp_path / "fix.txt").write_text("x\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    echt = subprocess.run

    def ohne_testlauf(args, *a, **k):
        if args[:3] == ["uv", "run", "pytest"]:
            return subprocess.CompletedProcess(args, 0, "", "")
        return echt(args, *a, **k)

    monkeypatch.setattr(hotfix.subprocess, "run", ohne_testlauf)
    ergebnis = finalize(tmp_path, hf_id)
    kopf = echt(["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True,
                text=True).stdout.strip()
    daten = _read_hf(tmp_path / ".sdd/hotfixes" / f"{hf_id}.md")
    assert ergebnis == kopf and daten["commit"] == kopf and len(kopf) == 40
    assert list(pruefer.iter_errors(daten)) == []


@pytest.mark.parametrize("wert,anzeige", [
    (HASH, "a1b2c3d"), ("2494608", "2494608"), ("", "—"), (None, "—")])
def test_anzeige_kuerzt_auf_sieben_zeichen(wert, anzeige):
    assert short_commit(wert) == anzeige


def test_alte_records_bleiben_lesbar(tmp_path):
    """INV-06: Records vor #132 (`commit: null`, Kurzhash) liest `sdd hotfix list` weiter."""
    d = tmp_path / ".sdd/hotfixes"
    d.mkdir(parents=True)
    (d / "HF-0001.md").write_text("---\nid: HF-0001\ndescription: alt\nstatus: open\n"
                                  "created: '2026-05-30'\ncommit: null\n---\n", encoding="utf-8")
    (d / "HF-0002.md").write_text("---\nid: HF-0002\ndescription: alt\nstatus: done\n"
                                  "created: '2026-05-30'\ncommit: 13e332e\n---\n", encoding="utf-8")
    assert [h["commit"] for h in list_hotfixes(tmp_path)] == [None, "13e332e"]
