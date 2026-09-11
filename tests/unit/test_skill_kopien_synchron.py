"""Die drei Kopien jeder Skill-Datei sind dieselbe Datei (#134).

Quelle ist das Blueprint (`tool/sdd_cli/blueprint/templates/agents-md/providers/`).
Daneben liegen `.claude/commands/` (die Skills dieses Repos, mit `scope:`-
Frontmatter für TST-0196) und `.sdd/templates/agents-md/providers/` (Projektkopie).
Bis #134 waren die Repo-Skills dem Blueprint voraus (Task-Routing, Pattern-Katalog,
ADR), das Blueprint den Repo-Skills (Befehlsnamen aus #91); jede Seite hatte etwas,
das der anderen fehlte, und ausgeliefert wurde die schlechtere.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_BLUEPRINT = _ROOT / "tool" / "sdd_cli" / "blueprint" / "templates" / "agents-md" / "providers" / "claude"
_REPO = _ROOT / ".claude" / "commands"
_PROJEKTKOPIE = _ROOT / ".sdd" / "templates" / "agents-md" / "providers" / "claude"

_FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)
_SKILLS = sorted(p.name for p in _BLUEPRINT.glob("*.md"))


def _ohne_frontmatter(text: str) -> str:
    return _FRONTMATTER_RE.sub("", text, count=1)


def test_es_gibt_skills():
    assert len(_SKILLS) >= 8


@pytest.mark.parametrize("name", _SKILLS)
def test_repo_skill_ist_blueprint_plus_scope(name):
    blueprint = (_BLUEPRINT / name).read_text(encoding="utf-8")
    repo = (_REPO / name).read_text(encoding="utf-8")
    if name != "sdd.md":  # TST-0196 verlangt scope: nur fuer sdd-*.md
        assert _FRONTMATTER_RE.match(repo), f".claude/commands/{name}: scope-Frontmatter fehlt"
    assert _ohne_frontmatter(repo) == blueprint, (
        f".claude/commands/{name} weicht vom Blueprint ab — Blueprint ändern, "
        f"dann die Kopie neu erzeugen (Frontmatter + Blueprint-Inhalt)"
    )


@pytest.mark.parametrize("name", _SKILLS)
def test_projektkopie_ist_das_blueprint(name):
    assert (_PROJEKTKOPIE / name).read_bytes() == (_BLUEPRINT / name).read_bytes(), (
        f".sdd/templates/agents-md/providers/claude/{name} weicht vom Blueprint ab"
    )
