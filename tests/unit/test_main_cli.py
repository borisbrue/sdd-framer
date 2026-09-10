"""Unit-Tests für main.py – Click CLI Commands via CliRunner (SPEC-0001)."""
from __future__ import annotations

import json
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
        # Zielort ist adr.output_dir, Default `docs/adr` im Projekt-Root —
        # so nennt es auch SPEC-0009 FR-01. Der Test erwartete .sdd/docs/adr.
        adrs = list((project / "docs" / "adr").glob("*.md"))
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


# ─── sdd autonomy set-level (frueher: sdd set-level) ──────────────────────────

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
        result = runner.invoke(cli, ["autonomy", "set-level", p.id, "2"])
        assert result.exit_code == 0
        assert p.id in result.output

    def test_set_level_invalid_exits_nonzero(self, runner, project, monkeypatch):
        monkeypatch.chdir(project)
        from sdd_cli.config import SddConfig
        cfg = SddConfig(root=project, raw={})
        p = create_project(cfg, name="My Project")
        result = runner.invoke(cli, ["autonomy", "set-level", p.id, "99"])
        assert result.exit_code != 0

    def test_set_level_unknown_project_exits_nonzero(self, runner, project, monkeypatch):
        monkeypatch.chdir(project)
        result = runner.invoke(cli, ["autonomy", "set-level", "PRJ-9999", "2"])
        assert result.exit_code != 0


# ─── sdd autonomy level (frueher: sdd level) ──────────────────────────────────

class TestLevelCmd:
    def test_level_shows_criteria_table(self, runner, project, monkeypatch):
        monkeypatch.chdir(project)
        from sdd_cli.config import SddConfig
        cfg = SddConfig(root=project, raw={})
        p = create_project(cfg, name="My Project")
        result = runner.invoke(cli, ["autonomy", "level", p.id])
        assert result.exit_code == 0
        assert "Level-Kriterien" in result.output

    def test_level_unknown_project_exits_nonzero(self, runner, project, monkeypatch):
        monkeypatch.chdir(project)
        result = runner.invoke(cli, ["autonomy", "level", "PRJ-9999"])
        assert result.exit_code != 0


# ─── sdd autonomy false-positive (frueher: sdd mark-false-positive) ───────────

class TestMarkFalsePositive:
    def test_mark_false_positive(self, runner, project, monkeypatch):
        monkeypatch.chdir(project)
        result = runner.invoke(cli, ["autonomy", "false-positive", "PR-0001", "--project", "PRJ-0001"])
        assert result.exit_code == 0
        assert "False Positive" in result.output

    def test_mark_false_positive_output_contains_pr(self, runner, project, monkeypatch):
        monkeypatch.chdir(project)
        result = runner.invoke(cli, ["autonomy", "false-positive", "PR-0042", "--project", "PRJ-0001"])
        assert "PR-0042" in result.output


# ─── sdd new agents-md (entfernt) ─────────────────────────────────────────────
#
# Die Tests hier legten die AGENTS.md ueber `sdd new agents-md` an. Den Befehl
# hat SPEC-0044 entfernt; die Datei entsteht seit #16 in `sdd init`. Der
# positive Weg ist in tests/unit/test_init_agents_md.py abgedeckt — hier bleibt
# der Migrationspfad: der Stub muss weiterverweisen statt still zu scheitern.

class TestNewAgentsMdEntfernt:
    def test_stub_endet_mit_fehler(self, runner, project, monkeypatch):
        monkeypatch.chdir(project)
        result = runner.invoke(cli, ["new", "agents-md"])
        assert result.exit_code == 1

    def test_stub_verweist_auf_sdd_init(self, runner, project, monkeypatch):
        monkeypatch.chdir(project)
        result = runner.invoke(cli, ["new", "agents-md"])
        assert "sdd init" in result.output


# ─── sdd new github-workflow (entfernt) ───────────────────────────────────────
#
# SPEC-0044 FR-06 wurde zurueckgenommen: der Workflow wird nicht angelegt, die
# Vorlage ist zu kopieren. Der Stub und seine Formulierung sind in
# tests/unit/test_github_workflow_removed.py abgedeckt.

class TestNewGithubWorkflowEntfernt:
    def test_stub_endet_mit_fehler(self, runner, project, monkeypatch):
        monkeypatch.chdir(project)
        result = runner.invoke(cli, ["new", "github-workflow"])
        assert result.exit_code == 1

    def test_stub_nennt_die_vorlage(self, runner, project, monkeypatch):
        monkeypatch.chdir(project)
        result = runner.invoke(cli, ["new", "github-workflow"])
        assert "sdd-orchestrate.yml" in result.output


# ─── sdd spec approve ─────────────────────────────────────────────────────────

def _write_spec_md(specs_dir: Path, spec_id: str, contracts: list, tests: list) -> None:
    contracts_yaml = json.dumps(contracts)
    tests_yaml = json.dumps(tests)
    content = (
        f"---\nid: {spec_id}\nstatus: review\n"
        f"contracts: {contracts_yaml}\ntests: {tests_yaml}\n---\n# Spec\n"
    )
    (specs_dir / f"{spec_id}-test.md").write_text(content, encoding="utf-8")


def _unlock_gate_up_to_regression_ok(project: Path, spec_id: str) -> None:
    phases_done = [
        "spec-draft", "spec-review", "contracts-proposed", "contracts-draft",
        "contracts-review", "tests-generated", "regression-ok",
    ]
    history = [
        {"phase": p, "completed_at": "2026-01-01T00:00:00Z", "result": "ok"}
        for p in phases_done
    ]
    data = {
        "spec_id": spec_id,
        "pipeline_phase": "regression-ok",
        "phase_history": history,
        "blocking_issues": [],
        "conflict_report_ref": None,
        "override": None,
    }
    gate_path = project / ".sdd" / "pipeline" / f"{spec_id}-gate.json"
    gate_path.parent.mkdir(parents=True, exist_ok=True)
    gate_path.write_text(json.dumps(data), encoding="utf-8")


class TestSpecApprove:
    def test_approve_fails_when_no_contracts(self, runner, project, monkeypatch):
        monkeypatch.chdir(project)
        _write_spec_md(project / ".sdd" / "specs", "SPEC-0099", contracts=[], tests=["TST-0001"])
        _unlock_gate_up_to_regression_ok(project, "SPEC-0099")
        result = runner.invoke(cli, ["spec", "approve", "SPEC-0099"])
        assert result.exit_code == 2
        assert "Contracts" in result.output

    def test_approve_fails_when_no_tests(self, runner, project, monkeypatch):
        monkeypatch.chdir(project)
        _write_spec_md(project / ".sdd" / "specs", "SPEC-0099", contracts=["CON-0001"], tests=[])
        _unlock_gate_up_to_regression_ok(project, "SPEC-0099")
        result = runner.invoke(cli, ["spec", "approve", "SPEC-0099"])
        assert result.exit_code == 2
        assert "Tests" in result.output

    def test_approve_fails_when_neither_contracts_nor_tests(self, runner, project, monkeypatch):
        monkeypatch.chdir(project)
        _write_spec_md(project / ".sdd" / "specs", "SPEC-0099", contracts=[], tests=[])
        _unlock_gate_up_to_regression_ok(project, "SPEC-0099")
        result = runner.invoke(cli, ["spec", "approve", "SPEC-0099"])
        assert result.exit_code == 2
        assert "Contracts" in result.output
        assert "Tests" in result.output

    def test_approve_succeeds_with_contracts_and_tests(self, runner, project, monkeypatch):
        monkeypatch.chdir(project)
        _write_spec_md(project / ".sdd" / "specs", "SPEC-0099",
                       contracts=["CON-0001"], tests=["TST-0001"])
        _unlock_gate_up_to_regression_ok(project, "SPEC-0099")
        result = runner.invoke(cli, ["spec", "approve", "SPEC-0099"])
        assert result.exit_code == 0
        assert "genehmigt" in result.output

    def test_approve_records_counts_in_gate(self, runner, project, monkeypatch):
        monkeypatch.chdir(project)
        _write_spec_md(project / ".sdd" / "specs", "SPEC-0099",
                       contracts=["CON-0001", "CON-0002"], tests=["TST-0001"])
        _unlock_gate_up_to_regression_ok(project, "SPEC-0099")
        runner.invoke(cli, ["spec", "approve", "SPEC-0099"])
        gate = json.loads(
            (project / ".sdd" / "pipeline" / "SPEC-0099-gate.json").read_text()
        )
        approved_entry = next(
            e for e in gate["phase_history"] if e["phase"] == "spec-approved"
        )
        assert approved_entry["consistency_check"]["contracts_count"] == 2
        assert approved_entry["consistency_check"]["tests_count"] == 1
