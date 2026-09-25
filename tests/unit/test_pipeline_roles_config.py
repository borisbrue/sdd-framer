"""SPEC-0053 FR-01/FR-02/FR-04: Rollendateien, Installation und Prüfung von llm.roles."""
from __future__ import annotations

from sdd_cli.config import SddConfig, load_config
from sdd_cli.config_validator import ConfigValidator
from sdd_cli.init import init_project
from sdd_cli.pipeline.providers import SAME_MODEL_WARNING, resolve_binding
from sdd_cli.pipeline.roles import BLUEPRINT_ROLES, DEFAULT_ROLES, install_roles, load_role
from sdd_cli.pipeline.runner import unknown_checks
from sdd_cli.validate import validate


def test_blueprint_rollen_sind_gueltig_und_kennen_ihre_checks(tmp_path):
    for rolle in DEFAULT_ROLES:
        definition = load_role(tmp_path, rolle)
        assert definition.source == BLUEPRINT_ROLES / f"{rolle}.md"
        assert unknown_checks(definition) == []


def test_install_roles_legt_new_nur_bei_abweichung_an(tmp_path):
    angelegt, neu, gleich = install_roles(tmp_path)
    assert len(angelegt) == len(DEFAULT_ROLES) and not neu and not gleich
    (tmp_path / ".sdd/roles/supervisor.md").write_text("eigene Rolle", encoding="utf-8")
    angelegt, neu, gleich = install_roles(tmp_path)
    assert not angelegt and [p.name for p in neu] == ["supervisor.md.new"]
    assert len(gleich) == len(DEFAULT_ROLES) - 1


def _issues(raw: dict, root):
    return [(i.level, i.path, i.message) for i in ConfigValidator(raw, root).validate()
            if i.path.startswith("llm.roles")]


def test_config_validate_warnt_bei_ignorierten_parametern(tmp_path):
    raw = {"llm": {"roles": {"decomposer": {"provider": "claude-cli",
                                            "base_url": "http://x/v1", "thinking": True}}}}
    assert ("warning", "llm.roles.decomposer.base_url", "wird von claude-cli ignoriert") \
        in _issues(raw, tmp_path)


def test_config_validate_meldet_fehler(tmp_path):
    raw = {"llm": {"roles": {"implementer": {"provider": "huggingface", "mode": "session"},
                             "reviewer": {"reasoning_effort": "extrem", "farbe": "blau"}}}}
    pfade = {(level, pfad) for level, pfad, _ in _issues(raw, tmp_path)}
    assert ("error", "llm.roles.implementer.provider") in pfade
    assert ("error", "llm.roles.reviewer.farbe") in pfade


def test_config_validate_warnt_bei_gleichem_modell(tmp_path):
    block = {"provider": "openai-compat", "base_url": "http://x/v1", "model": "qwen"}
    raw = {"llm": {"roles": {"implementer": block, "reviewer": dict(block)}}}
    assert ("warning", "llm.roles.reviewer", SAME_MODEL_WARNING) in _issues(raw, tmp_path)


def test_ohne_llm_roles_gilt_legacy_component(tmp_path):
    """FR-04: ohne llm.roles löst die Rolle über legacy_component auf (CON-0199 INV-04)."""
    raw = {"llm": {"completion": {"provider": "openai-compat", "base_url": "http://x/v1",
                                  "model": "alt"}}}
    binding = resolve_binding(SddConfig(root=tmp_path, raw=raw), load_role(tmp_path, "decomposer"))
    assert (binding.provider, binding.model, binding.source) == ("openai-compat", "alt",
                                                                 "legacy:completion")
    leer = resolve_binding(SddConfig(root=tmp_path, raw={}), load_role(tmp_path, "decomposer"))
    assert leer.provider == "claude-cli"


def test_validate_meldet_ungueltige_rolle(tmp_path):
    init_project(tmp_path, title="Rollen")
    pfad = tmp_path / ".sdd/roles/reviewer.md"
    pfad.write_text(pfad.read_text(encoding="utf-8").replace("checks: [json_schema]",
                                                             "checks: [json_schema, raten]"),
                    encoding="utf-8")
    meldungen = [i.message for i in validate(load_config(tmp_path)).issues
                 if i.file == pfad]
    assert any("raten" in m for m in meldungen)
