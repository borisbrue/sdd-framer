"""TST-0196 – Skill-Scope-Einträge im Frontmatter aller sdd-Skills (Unit)
Spec: SPEC-0044 · Contract: CON-0168
Prüft dass alle sdd-*.md Skill-Dateien einen scope:-Eintrag haben.
"""
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / ".claude" / "commands"

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
SCOPE_RE = re.compile(r"^scope:\s*(.+)$", re.MULTILINE)


def _skill_files() -> list[Path]:
    return sorted(SKILLS_DIR.glob("sdd-*.md"))


def _parse_scope(content: str) -> str | None:
    fm_match = FRONTMATTER_RE.match(content)
    if not fm_match:
        return None
    scope_match = SCOPE_RE.search(fm_match.group(1))
    return scope_match.group(1).strip() if scope_match else None


@pytest.mark.parametrize("skill_file", _skill_files(), ids=lambda p: p.name)
def test_skill_has_scope_entry(skill_file: Path):
    content = skill_file.read_text(encoding="utf-8")
    scope = _parse_scope(content)
    assert scope is not None, f"{skill_file.name}: fehlt 'scope:' im Frontmatter"
    assert len(scope) > 0, f"{skill_file.name}: 'scope:' darf nicht leer sein"


def test_at_least_one_skill_file_found():
    files = _skill_files()
    assert len(files) > 0, \
        f"Keine sdd-*.md Dateien in {SKILLS_DIR} — Skill-Dateien noch nicht angelegt?"
