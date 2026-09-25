"""Testprojekt für die Rollen-Pipeline (SPEC-0053).

Das Projekt hat keine Python-Quellen: Tests sind Shell-Skripte `tests/*.test.sh`, die Testsonde
führt sie aus und schreibt JUnit (FR-Markierung im Namen). Alle Rollen zeigen auf den
Fake-Server (`fake-<rolle>`), der Supervisor läuft `inline`, außer ein Test setzt `session`.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner, Result

from .fake_llm import FakeLLM

SPEC_ID = "SPEC-0900"
ROLLEN = ("decomposer", "test_author", "implementer", "reviewer", "supervisor")

RUN_TESTS = r'''#!/bin/sh
# Führt tests/*.test.sh aus und schreibt JUnit nach stdout.
printf '<testsuite name="shell">\n'
for t in tests/*.test.sh; do
  [ -e "$t" ] || continue
  name=$(basename "$t" .test.sh)
  if sh "$t" >/dev/null 2>&1; then
    printf '<testcase classname="tests" name="%s" file="%s"/>\n' "$name" "$t"
  else
    printf '<testcase classname="tests" name="%s" file="%s"><failure message="rot"/></testcase>\n' "$name" "$t"
  fi
done
printf '</testsuite>\n'
'''


def _cli_hat_pipeline() -> bool:
    from sdd_cli.main import cli

    return "pipeline" in cli.commands


requires_pipeline_cli = pytest.mark.skipif(
    not _cli_hat_pipeline(), reason="sdd pipeline noch nicht implementiert (SPEC-0053)")


# ── Antworten der Rollen ──────────────────────────────────────────────────────

def task(titel: str, frs: list[str], datei: str, typ: str = "code", deps: list[str] = ()) -> dict:
    slug = datei.rsplit("/", 1)[-1].removesuffix(".sh")
    return {"title": titel, "description": f"{titel} umsetzen", "type": typ, "complexity": "low",
            "fr_ids": frs, "dependencies": list(deps),
            "test_file": f"tests/t_{'_'.join(frs)}_{slug}.test.sh",
            "test_command": "sh .sdd/quality/run_tests.sh", "allowed_paths": [datei]}


def zerlegung(*tasks: dict) -> dict:
    return {"tasks": list(tasks)}


def rot_test(t: dict, erwartet: str = "ok") -> dict:
    ziel = t["allowed_paths"][0]
    return {"test_file": t["test_file"], "fr_ids": t["fr_ids"],
            "content": f'[ "$(sh {ziel} 2>/dev/null)" = "{erwartet}" ]\n'}


def implementierung(t: dict, ausgabe: str = "ok") -> dict:
    return {"files": [{"path": t["allowed_paths"][0], "content": f'echo "{ausgabe}"\n'}],
            "explanation": "implementiert"}


def review(ok: bool = True) -> dict:
    if ok:
        return {"verdict": "pass", "findings": []}
    return {"verdict": "fail", "findings": [{"category": "requirement", "file": "src/a.sh",
                                              "reason": "Anforderung nicht erfüllt"}]}


def command(point: str, name: str, **felder) -> dict:
    return {"point": point, "command": name, "reason": felder.pop("reason", "begründet"), **felder}


def abnahme(**status: str) -> dict:
    return command("S3", "accept_frs", frs=[{"id": fr.replace("_", "-"), "status": s,
                                            "evidence": "tests/"} for fr, s in status.items()])


# ── Projekt ───────────────────────────────────────────────────────────────────

@dataclass
class PipelineProject:
    root: Path
    llm: FakeLLM
    monkeypatch: pytest.MonkeyPatch

    def run(self, *args: str) -> Result:
        from sdd_cli.main import cli

        self.monkeypatch.chdir(self.root)
        return CliRunner().invoke(cli, list(args))

    def config(self, **aenderungen) -> None:
        pfad = self.root / ".sdd/config.yaml"
        daten = yaml.safe_load(pfad.read_text()) or {}
        for pfad_teile, wert in aenderungen.items():
            ziel = daten
            teile = pfad_teile.split("__")
            for t in teile[:-1]:
                ziel = ziel.setdefault(t, {})
            ziel[teile[-1]] = wert
        pfad.write_text(yaml.safe_dump(daten, sort_keys=False))

    def run_dir(self) -> Path:
        runs = sorted((self.root / ".sdd/runs" / SPEC_ID).iterdir())
        assert runs, "kein Run angelegt"
        return runs[-1]

    def json(self, name: str) -> dict:
        return json.loads((self.run_dir() / name).read_text())

    def jsonl(self, name: str) -> list[dict]:
        pfad = self.run_dir() / name
        return [json.loads(z) for z in pfad.read_text().splitlines() if z.strip()] if pfad.exists() else []

    def usage(self) -> list[dict]:
        db = self.root / ".sdd/evaluations.db"
        with sqlite3.connect(db) as con:
            con.row_factory = sqlite3.Row
            return [dict(r) for r in con.execute("SELECT * FROM token_usage")]


def make_pipeline_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                          llm: FakeLLM, frs: tuple[str, ...] = ("FR-01", "FR-02")) -> PipelineProject:
    from sdd_cli.gate import PHASE_ORDER, ExecutionGate
    from sdd_cli.init import init_project

    init_project(tmp_path, title="Pipeline-Testprojekt")
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir(exist_ok=True)
    (tmp_path / ".sdd/quality").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".sdd/quality/run_tests.sh").write_text(RUN_TESTS)
    (tmp_path / ".sdd/quality.yaml").write_text(yaml.safe_dump({"version": 1, "probes": {
        "tests": {"command": "sh .sdd/quality/run_tests.sh > {out}", "format": "junit",
                  "role": "tests", "fr_marker": "name"}}}))
    body = "\n".join(f"- **{fr}:** Anforderung {fr}." for fr in frs)
    (tmp_path / f".sdd/specs/{SPEC_ID}-testspec.md").write_text(
        f"---\nid: {SPEC_ID}\ntitle: Testspec\ntype: feature\nstatus: approved\nowner: Test\n"
        f"version: 0.1.0\ncontracts: []\ntests: []\n---\n\n# Testspec\n\n"
        f"## 4. Funktionale Anforderungen\n\n{body}\n")
    gate = ExecutionGate(tmp_path)
    for phase in PHASE_ORDER:
        gate.mark_phase_complete(SPEC_ID, phase)
    p = PipelineProject(tmp_path, llm, monkeypatch)
    rollen = {r: {"provider": "openai-compat", "base_url": llm.base_url, "model": f"fake-{r}",
                  "api_key": "fake"} for r in ROLLEN}
    rollen["supervisor"]["mode"] = "inline"
    p.config(llm__roles=rollen)
    return p
