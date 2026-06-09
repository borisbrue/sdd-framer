"""Unit-Tests für generate_holdouts.get_existing_hol_ids_for_spec (SPEC-0033)."""
from __future__ import annotations

from pathlib import Path

import pytest

from sdd_cli.generate_holdouts import get_existing_hol_ids_for_spec


@pytest.fixture()
def cfg(tmp_path: Path):
    from sdd_cli.config import SddConfig
    holdout_dir = tmp_path / ".sdd" / "holdout"
    holdout_dir.mkdir(parents=True)
    return SddConfig(root=tmp_path, raw={"ids": {"padding": 4}})


def _write_hol(holdout_dir: Path, hol_id: str, spec_id: str) -> None:
    path = holdout_dir / f"{hol_id}-test.md"
    path.write_text(
        f"---\nid: {hol_id}\nspec: {spec_id}\nstatus: ready\ntitle: Test\n---\n",
        encoding="utf-8",
    )


def test_returns_ids_for_matching_spec(cfg) -> None:
    holdout_dir = cfg.holdout_dir
    _write_hol(holdout_dir, "HOL-0001", "SPEC-0033")
    _write_hol(holdout_dir, "HOL-0002", "SPEC-0033")
    _write_hol(holdout_dir, "HOL-0003", "SPEC-9999")

    result = get_existing_hol_ids_for_spec("SPEC-0033", cfg)

    assert result == {"HOL-0001", "HOL-0002"}


def test_returns_empty_when_no_holdouts_exist(cfg) -> None:
    result = get_existing_hol_ids_for_spec("SPEC-0033", cfg)
    assert result == set()


def test_returns_empty_when_holdout_dir_missing(tmp_path: Path) -> None:
    from sdd_cli.config import SddConfig
    cfg = SddConfig(root=tmp_path, raw={"ids": {"padding": 4}})

    result = get_existing_hol_ids_for_spec("SPEC-0033", cfg)
    assert result == set()


def test_ignores_other_spec_holdouts(cfg) -> None:
    holdout_dir = cfg.holdout_dir
    _write_hol(holdout_dir, "HOL-0001", "SPEC-0001")
    _write_hol(holdout_dir, "HOL-0002", "SPEC-0002")

    result = get_existing_hol_ids_for_spec("SPEC-0033", cfg)
    assert result == set()
