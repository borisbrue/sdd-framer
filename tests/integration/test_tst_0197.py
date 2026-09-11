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
    # Hier stimmt der Verweis auf sdd init: seit #54 legt init die AGENTS.md an.
    assert "init" in combined, \
        "Fehlerausgabe muss auf 'sdd init' hinweisen"


def test_new_github_workflow_removed():
    result = _run(["new", "github-workflow"])
    assert result.returncode != 0, \
        "sdd new github-workflow muss nach Cleanup fehlschlagen"
    combined = (result.stdout + result.stderr).lower()
    # Der Hinweis lautete "in sdd init integriert" — das ist nie geschehen und
    # wurde mit SPEC-0044 v0.2.0 zurueckgenommen (FR-06). Die Ausgabe verweist
    # jetzt auf die Vorlage, die tatsaechlich existiert.
    assert "templates/github-actions" in combined, \
        "Fehlerausgabe muss auf die Vorlage hinweisen"


def test_upgrade_ruestet_fehlende_skills_nach(tmp_path):
    """CON-0169: `sdd upgrade` rüstet fehlende Skill-Dateien nach.

    Bis #126 prüfte dieser Test nur, ob `--help` das Wort erwähnt. Umgesetzt war
    die Nachrüstung nicht, der Test war trotzdem grün.
    """
    (tmp_path / ".sdd").mkdir()
    (tmp_path / ".sdd" / "config.yaml").write_text("project:\n  name: T\n", encoding="utf-8")
    eigen = tmp_path / ".claude" / "commands" / "sdd.md"
    eigen.parent.mkdir(parents=True)
    eigen.write_text("meins", encoding="utf-8")

    result = _run(["upgrade", "--path", str(tmp_path)])
    assert result.returncode == 0, result.stdout + result.stderr
    assert (tmp_path / ".claude" / "commands" / "sdd-implement.md").is_file()
    assert eigen.read_text(encoding="utf-8") == "meins"
