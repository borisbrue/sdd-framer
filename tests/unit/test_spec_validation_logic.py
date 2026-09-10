"""Unit-Tests für generate_holdouts.load_and_validate_spec (SPEC-0033)."""
from __future__ import annotations

from pathlib import Path

import pytest

from sdd_cli.generate_holdouts import load_and_validate_spec


@pytest.fixture()
def sdd_project(tmp_path: Path):
    sdd_dir = tmp_path / ".sdd"
    specs_dir = sdd_dir / "specs"
    specs_dir.mkdir(parents=True)
    (sdd_dir / "config.yaml").write_text(
        "ids:\n  padding: 4\n", encoding="utf-8"
    )
    return tmp_path


def _write_spec(specs_dir: Path, spec_id: str, status: str, contracts: list[str]) -> Path:
    contracts_yaml = "\n".join(f"  - {c}" for c in contracts)
    content = (
        f"---\nid: {spec_id}\ntitle: Test Spec\nstatus: {status}\n"
        f"contracts:\n{contracts_yaml}\n---\n# Body\n"
    )
    path = specs_dir / f"{spec_id}-test-spec.md"
    path.write_text(content, encoding="utf-8")
    return path


def test_returns_spec_data_for_approved_spec(sdd_project: Path) -> None:
    specs_dir = sdd_project / ".sdd" / "specs"
    _write_spec(specs_dir, "SPEC-0001", "approved", ["CON-0001", "CON-0002"])

    import yaml

    from sdd_cli.config import SddConfig
    cfg = SddConfig(root=sdd_project, raw=yaml.safe_load((sdd_project / ".sdd" / "config.yaml").read_text()))

    result = load_and_validate_spec("SPEC-0001", cfg)
    assert result["id"] == "SPEC-0001"
    assert result["status"] == "approved"
    assert "CON-0001" in result["contracts"]


def test_returns_spec_data_for_in_progress_spec(sdd_project: Path) -> None:
    specs_dir = sdd_project / ".sdd" / "specs"
    _write_spec(specs_dir, "SPEC-0002", "in-progress", ["CON-0001"])

    import yaml

    from sdd_cli.config import SddConfig
    cfg = SddConfig(root=sdd_project, raw=yaml.safe_load((sdd_project / ".sdd" / "config.yaml").read_text()))

    result = load_and_validate_spec("SPEC-0002", cfg)
    assert result["status"] == "in-progress"


def test_raises_for_draft_status(sdd_project: Path) -> None:
    specs_dir = sdd_project / ".sdd" / "specs"
    _write_spec(specs_dir, "SPEC-0003", "draft", ["CON-0001"])

    import yaml

    from sdd_cli.config import SddConfig
    cfg = SddConfig(root=sdd_project, raw=yaml.safe_load((sdd_project / ".sdd" / "config.yaml").read_text()))

    with pytest.raises(ValueError, match="approved oder in-progress"):
        load_and_validate_spec("SPEC-0003", cfg)


def test_raises_for_missing_spec(sdd_project: Path) -> None:
    import yaml

    from sdd_cli.config import SddConfig
    cfg = SddConfig(root=sdd_project, raw=yaml.safe_load((sdd_project / ".sdd" / "config.yaml").read_text()))

    with pytest.raises(FileNotFoundError, match="SPEC-9999 nicht gefunden"):
        load_and_validate_spec("SPEC-9999", cfg)


def test_raises_for_empty_contracts(sdd_project: Path) -> None:
    specs_dir = sdd_project / ".sdd" / "specs"
    _write_spec(specs_dir, "SPEC-0004", "approved", [])

    import yaml

    from sdd_cli.config import SddConfig
    cfg = SddConfig(root=sdd_project, raw=yaml.safe_load((sdd_project / ".sdd" / "config.yaml").read_text()))

    with pytest.raises(ValueError, match="Keine Contracts gefunden"):
        load_and_validate_spec("SPEC-0004", cfg)
