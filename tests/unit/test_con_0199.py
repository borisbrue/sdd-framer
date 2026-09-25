"""TST-0228 – CON-0199: Rollendefinition (Frontmatter von .sdd/roles/<rolle>.md).

Spec: SPEC-0053 · Contract: CON-0199
"""
from __future__ import annotations

import pytest

from tests.support.pipeline_project import requires_pipeline_cli
from tests.support.quality_project import schema_errors

GUELTIG = {"role": "decomposer", "version": "1.2.0",
           "purpose": "Zerlegt eine freigegebene Spec in Tasks.",
           "inputs": ["spec", "contracts", "agents_md", "repo_map"],
           "input_budgets": {"spec": 12000},
           "output_schema": "contracts/data/role-outputs.schema.json#/$defs/decomposer",
           "defaults": {"thinking": True, "max_output_tokens": 16000, "temperature": 0.6},
           "checks": ["json_schema", "fr_coverage", "acyclic"],
           "legacy_component": "completion"}


def test_tc01_valid_instance_passes():
    """Valide Instanz besteht Schema-Validierung (CON-0199)."""
    assert schema_errors("role_definition", GUELTIG) == []


def test_tc02_invalid_instance_rejected():
    """Beispiel aus dem Contract: holdout als Quelle, keine SemVer, Pflichtfelder fehlen."""
    assert schema_errors("role_definition", {"role": "decomposer", "version": "1",
                                             "inputs": ["spec", "holdout"], "checks": []})


def test_inv01_holdout_ist_keine_quelle():
    assert schema_errors("role_definition", {**GUELTIG, "inputs": ["spec", "holdout"]})


def test_inv02_supervisor_ohne_sonderfall():
    sup = {**GUELTIG, "role": "supervisor", "legacy_component": "evaluator",
           "output_schema": "contracts/data/supervisor-decision.schema.json"}
    assert schema_errors("role_definition", sup) == []
    assert schema_errors("role_definition", {**sup, "output_schema": None})


@pytest.mark.parametrize("version", ["1", "1.2", "v1.2.0", "1.2.0-rc"])
def test_inv05_semver(version):
    assert schema_errors("role_definition", {**GUELTIG, "version": version})


def test_inv04_legacy_component_geschlossen():
    assert schema_errors("role_definition", {**GUELTIG, "legacy_component": "irgendwas"})


def test_inv06_unbekannte_felder():
    assert schema_errors("role_definition", {**GUELTIG, "model": "qwen"})


def test_budget_nur_fuer_bekannte_quellen():
    assert schema_errors("role_definition", {**GUELTIG, "input_budgets": {"holdout": 10}})


ROLLEN = ("decomposer", "test_author", "implementer", "reviewer", "supervisor")


def _frontmatter(pfad):
    import yaml

    text = pfad.read_text(encoding="utf-8")
    return yaml.safe_load(text.split("---", 2)[1])


@requires_pipeline_cli
def test_fr02_init_installiert_gueltige_rollen(tmp_path):
    """SPEC-0053 FR-02: sdd init legt alle fünf Rollen an; jede Frontmatter erfüllt CON-0199."""
    from sdd_cli.init import init_project

    init_project(tmp_path, title="Rollen")
    for rolle in ROLLEN:
        pfad = tmp_path / ".sdd/roles" / f"{rolle}.md"
        assert pfad.is_file(), rolle
        fm = _frontmatter(pfad)
        assert fm["role"] == rolle and schema_errors("role_definition", fm) == []
        assert pfad.read_text(encoding="utf-8").split("---", 2)[2].strip(), "Prompt fehlt"


@requires_pipeline_cli
def test_fr02_upgrade_ueberschreibt_lokale_aenderung_nicht(tmp_path, monkeypatch):
    """SPEC-0053 FR-02: sdd upgrade legt bei lokal geänderter Rolle <rolle>.md.new an."""
    from click.testing import CliRunner

    from sdd_cli.init import init_project
    from sdd_cli.main import cli

    init_project(tmp_path, title="Rollen")
    pfad = tmp_path / ".sdd/roles/reviewer.md"
    eigen = pfad.read_text(encoding="utf-8") + "\nEigene Regel.\n"
    pfad.write_text(eigen, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    CliRunner().invoke(cli, ["upgrade"])
    assert pfad.read_text(encoding="utf-8") == eigen
    assert (tmp_path / ".sdd/roles/reviewer.md.new").is_file()
