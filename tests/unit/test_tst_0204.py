"""TST-0204 – sdd vision challenge – LLM- und Code-Challenge (Unit)
Spec: SPEC-0046 · Contract: CON-0178
"""
from unittest.mock import AsyncMock, patch

import pytest

SKELETON_WITH_FEATURE = """\
# Projekt – Produktvision

## Vision

## Zielgruppe

## Tech Stack

## Competitive Landscape

## Kernprobleme

## Features

1. **Offline-Modus** – App ohne Internet nutzbar

## Tasks
"""


class TestLLMChallengeStrategy:
    @pytest.mark.asyncio
    async def test_uses_ai_provider_interface(self, tmp_path):
        """INV-01: LLM-Aufruf via get_ai_provider(), kein direkter Provider-Zugriff."""
        from tool.sdd_cli.vision.challenge import LLMChallengeStrategy

        vision_file = tmp_path / "vision.md"
        vision_file.write_text(SKELETON_WITH_FEATURE)

        mock_provider = AsyncMock()
        mock_provider.complete.return_value = (
            "Aufwand: medium\nBegründung: Sync-Komplexität\nFallstricke: Konflikte"
        )

        with patch("tool.sdd_cli.vision.challenge.get_ai_provider",
                   return_value=mock_provider) as mock_get:
            strategy = LLMChallengeStrategy(vision_file=vision_file, config={})
            await strategy.challenge(feature_index=1)

        mock_get.assert_called_once_with({})
        mock_provider.complete.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_llm_result_saved_as_blockquote(self, tmp_path):
        """INV-05: Ergebnis als `> LLM Challenge:` inline unter Feature gespeichert."""
        from tool.sdd_cli.vision.challenge import LLMChallengeStrategy

        vision_file = tmp_path / "vision.md"
        vision_file.write_text(SKELETON_WITH_FEATURE)

        mock_provider = AsyncMock()
        mock_provider.complete.return_value = "Aufwand: high\nBegründung: Komplex"

        with patch("tool.sdd_cli.vision.challenge.get_ai_provider",
                   return_value=mock_provider):
            strategy = LLMChallengeStrategy(vision_file=vision_file, config={})
            await strategy.challenge(feature_index=1)

        content = vision_file.read_text()
        assert "> LLM Challenge:" in content

    @pytest.mark.asyncio
    async def test_llm_result_overwrites_existing(self, tmp_path):
        """INV-06: Bestehendes LLM-Challenge-Ergebnis wird überschrieben."""
        from tool.sdd_cli.vision.challenge import LLMChallengeStrategy

        content = SKELETON_WITH_FEATURE.replace(
            "1. **Offline-Modus** – App ohne Internet nutzbar",
            "1. **Offline-Modus** – App ohne Internet nutzbar\n   > LLM Challenge: Aufwand: low"
        )
        vision_file = tmp_path / "vision.md"
        vision_file.write_text(content)

        mock_provider = AsyncMock()
        mock_provider.complete.return_value = "Aufwand: high\nBegründung: Neu"

        with patch("tool.sdd_cli.vision.challenge.get_ai_provider",
                   return_value=mock_provider):
            strategy = LLMChallengeStrategy(vision_file=vision_file, config={})
            await strategy.challenge(feature_index=1)

        result = vision_file.read_text()
        assert result.count("> LLM Challenge:") == 1
        assert "Aufwand: low" not in result

    @pytest.mark.asyncio
    async def test_invalid_index_raises(self, tmp_path):
        """INV-04: Ungültiger Feature-Index → ValueError."""
        from tool.sdd_cli.vision.challenge import LLMChallengeStrategy

        vision_file = tmp_path / "vision.md"
        vision_file.write_text(SKELETON_WITH_FEATURE)

        with patch("tool.sdd_cli.vision.challenge.get_ai_provider",
                   return_value=AsyncMock()):
            strategy = LLMChallengeStrategy(vision_file=vision_file, config={})
            with pytest.raises(ValueError, match="99"):
                await strategy.challenge(feature_index=99)

    @pytest.mark.asyncio
    async def test_llm_challenge_is_async(self, tmp_path):
        """INV-02: challenge() ist eine Coroutine (async)."""
        import inspect

        from tool.sdd_cli.vision.challenge import LLMChallengeStrategy

        vision_file = tmp_path / "vision.md"
        vision_file.write_text(SKELETON_WITH_FEATURE)
        strategy = LLMChallengeStrategy(vision_file=vision_file, config={})
        assert inspect.iscoroutinefunction(strategy.challenge)


class TestCodeChallengeStrategy:
    def test_code_challenge_is_synchronous(self, tmp_path):
        """INV-03: challenge() ist keine Coroutine (synchron)."""
        import inspect

        from tool.sdd_cli.vision.challenge import CodeChallengeStrategy

        vision_file = tmp_path / "vision.md"
        vision_file.write_text(SKELETON_WITH_FEATURE)
        strategy = CodeChallengeStrategy(vision_file=vision_file, project_root=tmp_path)
        assert not inspect.iscoroutinefunction(strategy.challenge)

    def test_code_challenge_finds_matching_files(self, tmp_path):
        """INV-05: Matching-Dateien werden als > Code Challenge: gespeichert."""
        from tool.sdd_cli.vision.challenge import CodeChallengeStrategy

        vision_file = tmp_path / "vision.md"
        vision_file.write_text(SKELETON_WITH_FEATURE)

        src = tmp_path / "src"
        src.mkdir()
        (src / "offline_sync.py").write_text("# offline mode implementation")

        strategy = CodeChallengeStrategy(vision_file=vision_file, project_root=tmp_path)
        strategy.challenge(feature_index=1)

        content = vision_file.read_text()
        assert "> Code Challenge:" in content
        assert "offline_sync.py" in content

    def test_code_challenge_no_matches(self, tmp_path):
        """INV-07 (kein Match): Gibt 'Keine betroffenen Dateien gefunden.' aus."""
        from tool.sdd_cli.vision.challenge import CodeChallengeStrategy

        vision_file = tmp_path / "vision.md"
        vision_file.write_text(SKELETON_WITH_FEATURE)

        strategy = CodeChallengeStrategy(vision_file=vision_file, project_root=tmp_path)
        strategy.challenge(feature_index=1)

        assert "Keine betroffenen Dateien gefunden" in vision_file.read_text()

    def test_code_challenge_does_not_touch_llm_result(self, tmp_path):
        """INV-07: --code lässt > LLM Challenge: unverändert."""
        from tool.sdd_cli.vision.challenge import CodeChallengeStrategy

        content = SKELETON_WITH_FEATURE.replace(
            "1. **Offline-Modus** – App ohne Internet nutzbar",
            "1. **Offline-Modus** – App ohne Internet nutzbar\n   > LLM Challenge: Aufwand: low"
        )
        vision_file = tmp_path / "vision.md"
        vision_file.write_text(content)

        strategy = CodeChallengeStrategy(vision_file=vision_file, project_root=tmp_path)
        strategy.challenge(feature_index=1)

        assert "> LLM Challenge: Aufwand: low" in vision_file.read_text()

    def test_invalid_index_raises(self, tmp_path):
        """INV-04: Ungültiger Index → ValueError."""
        from tool.sdd_cli.vision.challenge import CodeChallengeStrategy

        vision_file = tmp_path / "vision.md"
        vision_file.write_text(SKELETON_WITH_FEATURE)
        strategy = CodeChallengeStrategy(vision_file=vision_file, project_root=tmp_path)

        with pytest.raises(ValueError, match="42"):
            strategy.challenge(feature_index=42)
