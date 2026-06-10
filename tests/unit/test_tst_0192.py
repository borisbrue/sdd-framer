"""TST-0192 – sdd-implement Schritt 5.5 Tier-Loop Inhalt (Unit)
Spec: SPEC-0042 · Contract: CON-0164
Prüft dass sdd-implement.md den tier-spezifischen Loop enthält (5.5a/5.5b/5.5c).
"""
from pathlib import Path

SKILL_PATH = Path(__file__).parents[2] / ".claude" / "commands" / "sdd-implement.md"


def _read_skill() -> str:
    return SKILL_PATH.read_text(encoding="utf-8")


def test_skill_contains_55a_critical_tier():
    content = _read_skill()
    assert "5.5a" in content or "Critical-Tier" in content, \
        "Schritt 5.5a (critical) fehlt in sdd-implement.md"


def test_skill_contains_55b_normal_tier():
    content = _read_skill()
    assert "5.5b" in content or "Normal-Tier" in content, \
        "Schritt 5.5b (normal) fehlt in sdd-implement.md"


def test_skill_contains_55c_edge_case_tier():
    content = _read_skill()
    assert "5.5c" in content or "Edge-Case-Tier" in content, \
        "Schritt 5.5c (edge-case) fehlt in sdd-implement.md"


def test_skill_uses_tier_flag_in_evaluate():
    content = _read_skill()
    assert "--tier critical" in content, "--tier critical fehlt in sdd-implement.md"
    assert "--tier normal" in content, "--tier normal fehlt in sdd-implement.md"
    assert "--tier edge-case" in content, "--tier edge-case fehlt in sdd-implement.md"


def test_skill_mentions_container_restart_on_critical():
    content = _read_skill()
    assert "Container neu starten" in content or "container-restart" in content.lower(), \
        "Container-Neustart-Anweisung bei critical-Fehler fehlt"
