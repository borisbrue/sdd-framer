"""Unit-Tests für main.py – Click CLI Commands via CliRunner (SPEC-0001)."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner

from sdd_cli.main import cli
from sdd_cli.projects import create_project


# ─── Fixtures ─────────────────────────────────────────────────────────────────

REAL_TEMPLATES = Path(__file__).parents[2] / ".sdd" / "templates"
REAL_SCHEMAS = Path(__file__).parents[2] / ".sdd" / "schemas"


def _setup_project(root: Path, project_name: str = "TestProject") -> None:
    sdd = root / ".sdd"
    sdd.mkdir(parents=True, exist_ok=True)
    (sdd / "specs").mkdir()
    (sdd / "contracts").mkdir()
    for sub in ["api", "data", "behavior", "performance"]:
        (sdd / "contracts" / sub).mkdir(parents=True)
    (sdd / "tests").mkdir()
    for sub in ["contract", "unit", "integration", "acceptance", "performance"]:
        (sdd / "tests" / sub).mkdir(parents=True)
    (sdd / "docs" / "adr").mkdir(parents=True)
    (sdd / "holdout").mkdir()
    (sdd / "projects").mkdir()
    (sdd / "evaluations").mkdir()

    config_content = f"project:\n  id: PRJ-0001\n  name: {project_name}\n"
    (sdd / "config.yaml").write_text(config_content, encoding="utf-8")

    if REAL_TEMPLATES.exists():
        shutil.copytree(REAL_TEMPLATES, sdd / "templates")
    if REAL_SCHEMAS.exists():
        shutil.copytree(REAL_SCHEMAS, sdd / "schemas")


@pytest.fixture()
def project(tmp_path: Path):
    _setup_project(tmp_path)
    return tmp_path


@pytest.fixture()
def runner():
    return CliRunner()


# ─── sdd --help ───────────────────────────────────────────────────────────────

class TestHelpAndVersion:
    def test_help_exits_zero(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Spec-Driven Development" in result.output

    def test_version_flag(self, runner):
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0

    def test_new_help(self, runner):
        result = runner.invoke(cli, ["new", "--help"])
        assert result.exit_code == 0
        assert "spec" in result.output

    def test_no_project_exits_nonzero(self, runner, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(cli, ["status"])
        assert result.exit_code != 0


# ─── sdd init ─────────────────────────────────────────────────────────────────

class TestInitCommand:
    def test_init_creates_sdd_dir(self, runner, tmp_path):
        target = tmp_path / "new_project"
        result = runner.invoke(cli, ["init", "--path", str(target), "--name", "MyProject"])
        assert result.exit_code == 0
        assert (target / ".sdd" / "config.yaml").exists()

    def test_init_output_contains_confirmation(self, runner, tmp_path):
        target = tmp_path / "proj"
        result = runner.invoke(cli, ["init", "--path", str(target)])
        assert "SDD-Projekt initialisiert" in result.output

    def test_init_force_flag_accepted(self, runner, tmp_path):
        target = tmp_path / "proj"
        runner.invoke(cli, ["init", "--path", str(target), "--name", "First"])
        result = runner.invoke(cli, ["init", "--path", str(target), "--name", "Second", "--force"])
        assert result.exit_code == 0
        content = (target / ".sdd" / "config.yaml").read_text()
        assert "Second" in content


# ─── sdd new spec ─────────────────────────────────────────────────────────────

class TestNewSpec:
    def test_new_spec_creates_file(self, runner, project, monkeypatch):
        monkeypatch.chdir(project)
        result = runner.invoke(cli, ["new", "spec", "My Feature"])
        assert result.exit_code == 0
        specs = list((project / ".sdd" / "specs").glob("*.md"))
        assert len(specs) == 1

    def test_new_spec_output_contains_id(self, runner, project, monkeypatch):
        monkeypatch.chdir(project)
        result = runner.invoke(cli, ["new", "spec", "Test Feature"])
        assert "SPEC-" in result.output

    def test_new_spec_with_owner(self, runner, project, monkeypatch):
        monkeypatch.chdir(project)
        result = runner.invoke(cli, ["new", "spec", "Feature", "--owner", "boris"])
        assert result.exit_code == 0

    def test_second_spec_gets_incremented_id(self, runner, project, monkeypatch):
        monkeypatch.chdir(project)
        runner.invoke(cli, ["new", "spec", "Feature A"])
        runner.invoke(cli, ["new", "spec", "Feature B"])
        specs = sorted((project / ".sdd" / "specs").glob("*.md"))
        assert len(specs) == 2
        assert "0001" in specs[0].name
        assert "0002" in specs[1].name


# ─── sdd new adr ──────────────────────────────────────────────────────────────

class TestNewAdr:
    def test_new_adr_creates_file(self, runner, project, monkeypatch):
        monkeypatch.chdir(project)
        result = runner.invoke(cli, ["new", "adr", "Use Postgres"])
        assert result.exit_code == 0
        adrs = list((project / ".sdd" / "docs" / "adr").glob("*.md"))
        assert len(adrs) == 1

    def test_new_adr_output_contains_id(self, runner, project, monkeypatch):
        monkeypatch.chdir(project)
        result = runner.invoke(cli, ["new", "adr", "Use Redis"])
        assert "ADR-" in result.output


# ─── sdd status ───────────────────────────────────────────────────────────────

class TestStatus:
    def test_status_empty_project(self, runner, project, monkeypatch):
        monkeypatch.chdir(project)
        result = runner.invoke(cli, ["status"])
        assert result.exit_code == 0
        assert "SDD-Projekt-Status" in result.output

    def test_status_shows_spec(self, runner, project, monkeypatch):
        monkeypatch.chdir(project)
        runner.invoke(cli, ["new", "spec", "My Feature"])
        result = runner.invoke(cli, ["status"])
        assert "SPEC-0001" in result.output


# ─── sdd validate ─────────────────────────────────────────────────────────────

class TestValidate:
    def test_validate_empty_project_exits_zero(self, runner, project, monkeypatch):
        monkeypatch.chdir(project)
        result = runner.invoke(cli, ["validate"])
        # No errors → exit 0; warnings (e.g. missing AGENTS.md) are acceptable
        assert result.exit_code == 0

    def test_validate_instruct_flag_outputs_json(self, runner, project, monkeypatch):
        monkeypatch.chdir(project)
        result = runner.invoke(cli, ["validate", "--instruct"])
        # --instruct exits 0 when no errors (warnings don't count without --strict)
        assert result.exit_code == 0
        # Output contains JSON keys (Rich may add ANSI codes, check for key presence)
        assert '"issues"' in result.output
        assert '"ok"' in result.output


# ─── sdd trace ────────────────────────────────────────────────────────────────

class TestTrace:
    def test_trace_creates_matrix_file(self, runner, project, monkeypatch):
        monkeypatch.chdir(project)
        result = runner.invoke(cli, ["trace"])
        assert result.exit_code == 0
        matrix = project / "docs" / "traceability.md"
        assert matrix.exists()

    def test_trace_output_confirms_update(self, runner, project, monkeypatch):
        monkeypatch.chdir(project)
        result = runner.invoke(cli, ["trace"])
        assert "Traceability-Matrix" in result.output


# ─── sdd set-level ────────────────────────────────────────────────────────────

class TestSetLevel:
    def _create_test_project(self, cfg_root: Path) -> None:
        from sdd_cli.config import SddConfig
        cfg = SddConfig(root=cfg_root, raw={})
        create_project(cfg, name="My Project", owner="boris")

    def test_set_level_valid(self, runner, project, monkeypatch):
        monkeypatch.chdir(project)
        from sdd_cli.config import SddConfig
        cfg = SddConfig(root=project, raw={})
        p = create_project(cfg, name="My Project")
        result = runner.invoke(cli, ["set-level", p.id, "2"])
        assert result.exit_code == 0
        assert p.id in result.output

    def test_set_level_invalid_exits_nonzero(self, runner, project, monkeypatch):
        monkeypatch.chdir(project)
        from sdd_cli.config import SddConfig
        cfg = SddConfig(root=project, raw={})
        p = create_project(cfg, name="My Project")
        result = runner.invoke(cli, ["set-level", p.id, "99"])
        assert result.exit_code != 0

    def test_set_level_unknown_project_exits_nonzero(self, runner, project, monkeypatch):
        monkeypatch.chdir(project)
        result = runner.invoke(cli, ["set-level", "PRJ-9999", "2"])
        assert result.exit_code != 0


# ─── sdd level ────────────────────────────────────────────────────────────────

class TestLevelCmd:
    def test_level_shows_criteria_table(self, runner, project, monkeypatch):
        monkeypatch.chdir(project)
        from sdd_cli.config import SddConfig
        cfg = SddConfig(root=project, raw={})
        p = create_project(cfg, name="My Project")
        result = runner.invoke(cli, ["level", p.id])
        assert result.exit_code == 0
        assert "Level-Kriterien" in result.output

    def test_level_unknown_project_exits_nonzero(self, runner, project, monkeypatch):
        monkeypatch.chdir(project)
        result = runner.invoke(cli, ["level", "PRJ-9999"])
        assert result.exit_code != 0


# ─── sdd mark-false-positive ──────────────────────────────────────────────────

class TestMarkFalsePositive:
    def test_mark_false_positive(self, runner, project, monkeypatch):
        monkeypatch.chdir(project)
        result = runner.invoke(cli, ["mark-false-positive", "PR-0001", "--project", "PRJ-0001"])
        assert result.exit_code == 0
        assert "False Positive" in result.output

    def test_mark_false_positive_output_contains_pr(self, runner, project, monkeypatch):
        monkeypatch.chdir(project)
        result = runner.invoke(cli, ["mark-false-positive", "PR-0042", "--project", "PRJ-0001"])
        assert "PR-0042" in result.output


# ─── sdd new agents-md ────────────────────────────────────────────────────────

class TestNewAgentsMd:
    def test_creates_agents_md(self, runner, project, monkeypatch):
        monkeypatch.chdir(project)
        result = runner.invoke(cli, ["new", "agents-md"])
        assert result.exit_code == 0
        assert (project / "AGENTS.md").exists()

    def test_second_call_warns_already_exists(self, runner, project, monkeypatch):
        monkeypatch.chdir(project)
        runner.invoke(cli, ["new", "agents-md"])
        result = runner.invoke(cli, ["new", "agents-md"])
        assert "existiert bereits" in result.output


# ─── sdd new github-workflow ──────────────────────────────────────────────────

class TestNewGithubWorkflow:
    def test_creates_workflow_file(self, runner, project, monkeypatch):
        monkeypatch.chdir(project)
        result = runner.invoke(cli, ["new", "github-workflow"])
        assert result.exit_code == 0
        wf = project / ".github" / "workflows" / "sdd-orchestrate.yml"
        assert wf.exists()

    def test_second_call_warns_already_exists(self, runner, project, monkeypatch):
        monkeypatch.chdir(project)
        runner.invoke(cli, ["new", "github-workflow"])
        result = runner.invoke(cli, ["new", "github-workflow"])
        assert "existiert bereits" in result.output
