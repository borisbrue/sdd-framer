"""Unit-Tests für generate_holdouts.resolve_contract_files (SPEC-0033)."""
from __future__ import annotations

from pathlib import Path

import pytest

from sdd_cli.generate_holdouts import resolve_contract_files


@pytest.fixture()
def cfg(tmp_path: Path):
    from sdd_cli.config import SddConfig
    sdd_dir = tmp_path / ".sdd"
    contracts_dir = sdd_dir / "contracts"
    contracts_dir.mkdir(parents=True)
    (sdd_dir / "config.yaml").write_text("ids:\n  padding: 4\n", encoding="utf-8")
    return SddConfig(root=tmp_path, raw={"ids": {"padding": 4}})


def _write_contract(contracts_dir: Path, cid: str, title: str = "Test") -> Path:
    path = contracts_dir / f"{cid}-test.md"
    path.write_text(
        f"---\nid: {cid}\ntitle: {title}\nstatus: approved\n---\n# Body\n",
        encoding="utf-8",
    )
    return path


def test_finds_existing_contracts(cfg) -> None:
    contracts_dir = cfg.root / ".sdd" / "contracts"
    _write_contract(contracts_dir, "CON-0001", "Contract One")
    _write_contract(contracts_dir, "CON-0002", "Contract Two")

    result = resolve_contract_files(["CON-0001", "CON-0002"], cfg)

    assert len(result) == 2
    ids = {r["id"] for r in result}
    assert ids == {"CON-0001", "CON-0002"}


def test_skips_missing_contracts(cfg) -> None:
    contracts_dir = cfg.root / ".sdd" / "contracts"
    _write_contract(contracts_dir, "CON-0001")

    result = resolve_contract_files(["CON-0001", "CON-9999"], cfg)

    assert len(result) == 1
    assert result[0]["id"] == "CON-0001"


def test_returns_empty_for_all_missing(cfg) -> None:
    result = resolve_contract_files(["CON-9999"], cfg)
    assert result == []


def test_result_has_required_keys(cfg) -> None:
    contracts_dir = cfg.root / ".sdd" / "contracts"
    _write_contract(contracts_dir, "CON-0001")

    result = resolve_contract_files(["CON-0001"], cfg)

    item = result[0]
    assert "id" in item
    assert "path" in item
    assert "content" in item
    assert "frontmatter" in item
