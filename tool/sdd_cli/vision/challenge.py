from __future__ import annotations

import re
from pathlib import Path

from .document import VisionDocument

_CODE_EXTENSIONS = {".py", ".ts", ".js", ".tsx", ".jsx", ".go", ".rs", ".java", ".rb", ".sh"}


def get_ai_provider(config):
    from ..llm.factory import get_completion_provider
    return get_completion_provider(config, "ai_routes")


class LLMChallengeStrategy:
    def __init__(self, vision_file: Path, config) -> None:
        self.vision_file = vision_file
        self.config = config

    async def challenge(self, feature_index: int) -> None:
        doc = VisionDocument.from_file(self.vision_file)
        if feature_index < 1 or feature_index > len(doc.features):
            raise ValueError(f"Feature-Index {feature_index} nicht gefunden")

        feature = doc.features[feature_index - 1]
        prompt = (
            f"Bewerte den Implementierungsaufwand für diese Feature-Idee:\n\n"
            f"Titel: {feature.title}\n"
            f"Beschreibung: {feature.description}\n\n"
            "Antwort: Aufwand (low/medium/high/unknown), Begründung, Fallstricke."
        )

        provider = get_ai_provider(self.config)
        result = await provider.complete(prompt)

        result_text = result.text if hasattr(result, "text") else str(result)
        feature.llm_challenge = result_text
        doc.save()


class CodeChallengeStrategy:
    def __init__(self, vision_file: Path, project_root: Path) -> None:
        self.vision_file = vision_file
        self.project_root = project_root

    def challenge(self, feature_index: int) -> None:
        doc = VisionDocument.from_file(self.vision_file)
        if feature_index < 1 or feature_index > len(doc.features):
            raise ValueError(f"Feature-Index {feature_index} nicht gefunden")

        feature = doc.features[feature_index - 1]
        keywords = _extract_keywords(feature.title, feature.description)
        matches = _find_matching_files(keywords, self.project_root)

        if matches:
            feature.code_challenge = ", ".join(matches)
        else:
            feature.code_challenge = "Keine betroffenen Dateien gefunden."
        doc.save()


def _extract_keywords(title: str, description: str) -> list[str]:
    text = f"{title} {description}"
    words = re.split(r"[^a-zA-ZäöüÄÖÜ]+", text)
    return [w.lower() for w in words if len(w) >= 4]


def _find_matching_files(keywords: list[str], project_root: Path) -> list[str]:
    seen: set[Path] = set()
    matches: list[str] = []

    for ext in _CODE_EXTENSIONS:
        for fpath in sorted(project_root.rglob(f"*{ext}")):
            if fpath in seen:
                continue
            stem_lower = fpath.stem.lower()
            if any(kw in stem_lower for kw in keywords):
                seen.add(fpath)
                matches.append(str(fpath.relative_to(project_root)))
                continue
            try:
                content_lower = fpath.read_text(errors="ignore").lower()
                if any(kw in content_lower for kw in keywords):
                    seen.add(fpath)
                    matches.append(str(fpath.relative_to(project_root)))
            except (OSError, PermissionError):
                pass

    return matches
