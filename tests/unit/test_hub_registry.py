"""Hub ProjectRegistry – register, get_all, update_status, duplicate-check."""
from __future__ import annotations

from pathlib import Path

import pytest

from sdd_cli.hub.models import ProjectEntry
from sdd_cli.hub.registry import DuplicateProjectError, ProjectNotFoundError, ProjectRegistry


def _entry(name: str = "myapp", port: int = 3000) -> ProjectEntry:
    return ProjectEntry(id=name, name=name, path=Path("/tmp"), start_cmd=["python", "app.py"], port=port)


def test_register_and_get_all(tmp_path):
    reg = ProjectRegistry(tmp_path / "registry.yaml")
    reg.register(_entry("app1"))
    entries = reg.get_all()
    assert len(entries) == 1
    assert entries[0].id == "app1"


def test_register_duplicate_raises(tmp_path):
    reg = ProjectRegistry(tmp_path / "registry.yaml")
    reg.register(_entry("app1"))
    with pytest.raises(DuplicateProjectError):
        reg.register(_entry("app1"))


def test_register_duplicate_with_force(tmp_path):
    reg = ProjectRegistry(tmp_path / "registry.yaml")
    reg.register(_entry("app1", port=3000))
    reg.register(_entry("app1", port=4000), force=True)
    assert reg.get("app1").port == 4000


def test_update_status(tmp_path):
    reg = ProjectRegistry(tmp_path / "registry.yaml")
    reg.register(_entry("app1"))
    reg.update_status("app1", "running", pid=1234)
    assert reg.get("app1").status == "running"
    assert reg.get("app1").pid == 1234


def test_update_status_unknown_raises(tmp_path):
    reg = ProjectRegistry(tmp_path / "registry.yaml")
    with pytest.raises(ProjectNotFoundError):
        reg.update_status("unknown", "running", pid=None)


def test_persistence_across_instances(tmp_path):
    path = tmp_path / "registry.yaml"
    reg1 = ProjectRegistry(path)
    reg1.register(_entry("persistent"))
    reg2 = ProjectRegistry(path)
    assert len(reg2.get_all()) == 1
    assert reg2.get("persistent").id == "persistent"


def test_remove_entry(tmp_path):
    reg = ProjectRegistry(tmp_path / "registry.yaml")
    reg.register(_entry("to-remove"))
    reg.remove("to-remove")
    assert len(reg.get_all()) == 0
