"""TST-0197 – sdd init Scaffolding-Integration (Integration)
Spec: SPEC-0044 · Contract: CON-0169
Prüft dass sdd new agents-md/github-workflow entfernt und sdd upgrade vorhanden ist.
"""
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["sdd"] + args,
        capture_output=True, text=True, cwd=REPO_ROOT
    )


def test_new_agents_md_removed():
    result = _run(["new", "agents-md"])
    assert result.returncode != 0, \
        "sdd new agents-md muss nach Cleanup fehlschlagen"
    combined = (result.stdout + result.stderr).lower()
    assert "init" in combined, \
        "Fehlerausgabe muss auf 'sdd init' hinweisen"


def test_new_github_workflow_removed():
    result = _run(["new", "github-workflow"])
    assert result.returncode != 0, \
        "sdd new github-workflow muss nach Cleanup fehlschlagen"
    combined = (result.stdout + result.stderr).lower()
    assert "init" in combined, \
        "Fehlerausgabe muss auf 'sdd init' hinweisen"


def test_upgrade_has_skill_retrofit_logic():
    result = _run(["upgrade", "--help"])
    assert result.returncode == 0, "sdd upgrade --help muss Exit 0 liefern"
    combined = (result.stdout + result.stderr).lower()
    assert "skill" in combined or "agent" in combined or "commands" in combined, \
        "sdd upgrade --help muss Skill-Nachrüstung erwähnen"
