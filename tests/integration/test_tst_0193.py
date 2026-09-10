"""TST-0193 – CLI-Gruppen `pattern` und `dev` entfernt (Integration)
Spec: SPEC-0044 · Contract: CON-0165
Prüft dass pattern/dev-Gruppen entfernt und obsidian/pwa erhalten sind.
"""
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["sdd"] + args,
        capture_output=True, text=True, cwd=REPO_ROOT
    )


def test_pattern_group_removed():
    result = _run(["pattern", "list"])
    assert result.returncode != 0, "sdd pattern list muss nach Cleanup fehlschlagen"


def test_dev_group_removed():
    result = _run(["dev", "start"])
    assert result.returncode != 0, "sdd dev start muss nach Cleanup fehlschlagen"


def test_obsidian_group_intact():
    result = _run(["obsidian", "--help"])
    assert result.returncode == 0, "sdd obsidian --help muss funktionieren"


def test_pwa_group_intact():
    result = _run(["pwa", "--help"])
    assert result.returncode == 0, "sdd pwa --help muss funktionieren"


def test_changelog_contains_pattern_migration_note():
    changelog = REPO_ROOT / "CHANGELOG.md"
    assert changelog.exists(), "CHANGELOG.md fehlt"
    content = changelog.read_text(encoding="utf-8").lower()
    assert "pattern" in content, "CHANGELOG.md enthält keinen Hinweis auf entfernte pattern-Gruppe"


def test_changelog_contains_dev_migration_note():
    changelog = REPO_ROOT / "CHANGELOG.md"
    content = changelog.read_text(encoding="utf-8").lower()
    assert "sdd dev" in content or ("dev" in content and "entfernt" in content), \
        "CHANGELOG.md enthält keinen Hinweis auf entfernte dev-Gruppe"
