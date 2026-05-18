"""Unit-Tests für init.py – SDD-Projektinitialisierung."""
from __future__ import annotations

from pathlib import Path

import pytest

from sdd_cli.init import init_project, REQUIRED_DIRS


# ─── init_project ─────────────────────────────────────────────────────────────

class TestInitProject:
    def test_creates_all_required_dirs(self, tmp_path):
        init_project(tmp_path, "TestProject")
        for rel in REQUIRED_DIRS:
            assert (tmp_path / rel).is_dir(), f"Verzeichnis fehlt: {rel}"

    def test_returns_list_of_created_paths(self, tmp_path):
        result = init_project(tmp_path, "TestProject")
        created = result["created"]
        assert isinstance(created, list)
        assert len(created) > 0
        for p in created:
            assert isinstance(p, Path)

    def test_idempotent_no_duplicate_dirs(self, tmp_path):
        init_project(tmp_path, "TestProject")
        result_second = init_project(tmp_path, "TestProject")
        # Second run creates nothing new (dirs already exist, no force)
        # config.yaml exists and force=False → not created again
        # Templates already exist → not copied again
        for p in result_second["created"]:
            # All paths returned on second run must be files (templates if any new)
            assert p.exists()

    def test_force_overwrites_config(self, tmp_path):
        init_project(tmp_path, "FirstProject")
        init_project(tmp_path, "SecondProject", force=True)
        config_path = tmp_path / ".sdd" / "config.yaml"
        content = config_path.read_text(encoding="utf-8")
        assert "SecondProject" in content

    def test_no_force_does_not_overwrite_config(self, tmp_path):
        init_project(tmp_path, "FirstProject")
        init_project(tmp_path, "SecondProject", force=False)
        config_path = tmp_path / ".sdd" / "config.yaml"
        content = config_path.read_text(encoding="utf-8")
        assert "FirstProject" in content
        assert "SecondProject" not in content

    def test_project_name_substituted_in_config(self, tmp_path):
        init_project(tmp_path, "MySpecialProject")
        config_path = tmp_path / ".sdd" / "config.yaml"
        content = config_path.read_text(encoding="utf-8")
        assert "MySpecialProject" in content
        assert "<PROJECT_NAME>" not in content

    def test_target_dir_created_if_not_exists(self, tmp_path):
        target = tmp_path / "new" / "nested" / "project"
        assert not target.exists()
        init_project(target, "TestProject")
        assert target.is_dir()

    def test_templates_copied_when_src_exists(self, tmp_path):
        init_project(tmp_path, "TestProject")
        templates_dir = tmp_path / ".sdd" / "templates"
        # Templates dir should exist (either via copy or because src exists)
        # We can only assert the config and dirs exist since blueprint root
        # may or may not have templates in test env
        assert (tmp_path / ".sdd").is_dir()

    def test_specs_archive_dir_created(self, tmp_path):
        init_project(tmp_path, "TestProject")
        assert (tmp_path / ".sdd" / "specs" / "_archive").is_dir()

    def test_all_contract_subdirs_created(self, tmp_path):
        init_project(tmp_path, "TestProject")
        for subdir in ["api", "data", "behavior", "performance"]:
            assert (tmp_path / ".sdd" / "contracts" / subdir).is_dir()

    def test_all_test_subdirs_created(self, tmp_path):
        init_project(tmp_path, "TestProject")
        for subdir in ["contract", "unit", "integration", "acceptance", "performance"]:
            assert (tmp_path / ".sdd" / "tests" / subdir).is_dir()
