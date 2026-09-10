# TST-0126 – /sdd-config Claude-Code-Skill (Unit)
# Spec: SPEC-0027 | Contract: CON-0107

from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
SKILL_PATH = _PROJECT_ROOT / ".claude" / "commands" / "sdd-config.md"


def _skill_content() -> str:
    return SKILL_PATH.read_text(encoding="utf-8")


class TestTST0126:
    def test_skill_file_exists(self):
        assert SKILL_PATH.exists(), f"Skill-Datei fehlt: {SKILL_PATH}"

    def test_skill_reads_config_yaml_on_start(self):
        content = _skill_content()
        assert "config.yaml" in content

    def test_skill_requires_explicit_confirmation_before_write(self):
        content = _skill_content()
        assert "Bestätigung" in content or "bestätigung" in content.lower() or "ja" in content

    def test_skill_never_suggests_plaintext_api_keys(self):
        content = _skill_content()
        assert "Klartext-API-Key" in content or "NIEMALS" in content.upper() or "nie" in content.lower()

    def test_skill_prohibits_holdout_access(self):
        content = _skill_content()
        assert "holdout" in content.lower()

    def test_skill_aborts_when_config_missing(self):
        content = _skill_content()
        assert "sdd init" in content

    def test_skill_runs_validate_after_write(self):
        content = _skill_content()
        assert "sdd config validate" in content
