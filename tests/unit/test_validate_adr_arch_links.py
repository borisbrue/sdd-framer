"""SPEC-0054 FR-06, CON-0197 INV-07/INV-08: Verknüpfung architecture.yaml ↔ ADRs."""
from __future__ import annotations

import yaml

from sdd_cli.quality.arch.adr_links import check_adr_links


def _adr(root, adr_id, status="accepted", enforced_by=()):
    (root / "docs/adr").mkdir(parents=True, exist_ok=True)
    (root / f"docs/adr/{adr_id}-x.md").write_text("---\n" + yaml.safe_dump(
        {"id": adr_id, "title": "T", "status": status, "enforced_by": list(enforced_by)})
        + "---\n")


def _arch(root, rules):
    (root / ".sdd").mkdir(exist_ok=True)
    (root / ".sdd/architecture.yaml").write_text(yaml.safe_dump(
        {"version": 1, "layers": {"a": ["a/**"], "b": ["b/**"]}, "rules": rules}))


def _r(rid, adr, **kw):
    return {"id": rid, "adr": adr, "kind": "forbidden_dependency", "from": "a",
            "to_layers": ["b"], **kw}


def _funde(root):
    return {(f.level, f.message) for f in check_adr_links(root, "docs/adr")}


def test_ohne_architecture_yaml_nichts(tmp_path):
    _adr(tmp_path, "ADR-0007", enforced_by=("ARCH-09",))
    assert check_adr_links(tmp_path, "docs/adr") == []


def test_fehler_und_warnungen(tmp_path):
    _adr(tmp_path, "ADR-0007", enforced_by=("ARCH-09",))
    _adr(tmp_path, "ADR-0008", status="superseded")
    _arch(tmp_path, [_r("ARCH-05", "ADR-0099"), _r("ARCH-02", "ADR-0008"),
                     _r("ARCH-03", "ADR-0007"), _r("ARCH-03", "ADR-0007"),
                     _r("ARCH-04", "ADR-0007", **{"from": "zz"})])
    levels = {}
    for level, msg in _funde(tmp_path):
        levels.setdefault(level, []).append(msg)
    fehler, warn = " | ".join(levels["error"]), " | ".join(levels["warning"])
    assert "ARCH-05" in fehler and "ADR-0099" in fehler
    assert "doppelte Regel-ID ARCH-03" in fehler
    assert "ARCH-04" in fehler and "unbekannte Schicht" in fehler
    assert "ADR-0007" in warn and "ARCH-09" in warn
    assert "ARCH-02" in warn and "ADR-0008" in warn


def test_taste_invariants_ohne_regel_als_hinweis(tmp_path):
    _adr(tmp_path, "ADR-0007")
    _arch(tmp_path, [_r("ARCH-01", "ADR-0007")])
    (tmp_path / "AGENTS.md").write_text("## Taste Invariants\n\n- **A:** mit Regel [ARCH-01]\n"
                                        "- **B:** ohne Regel\n\n## Weiter\n")
    hinweise = [m for lvl, m in _funde(tmp_path) if lvl == "info"]
    assert len(hinweise) == 1 and "B" in hinweise[0]
