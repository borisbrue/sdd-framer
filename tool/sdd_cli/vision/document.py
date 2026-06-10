from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


class VisionNotFoundError(FileNotFoundError):
    pass


REQUIRED_HEADINGS = [
    "## Vision",
    "## Zielgruppe",
    "## Tech Stack",
    "## Competitive Landscape",
    "## Kernprobleme",
    "## Features",
    "## Tasks",
]

_FEATURE_RE = re.compile(r"^(\d+)\. \*\*(.+?)\*\*(?:\s+–\s*(.*))?$")
_BLOCKQUOTE_RE = re.compile(r"^\s+>\s+(LLM Challenge|Code Challenge):\s*(.*)$")
_TASK_RE = re.compile(r"^- \[( |x)\] (.+)$")


@dataclass
class VisionTask:
    title: str
    done: bool = False


@dataclass
class VisionFeature:
    title: str
    description: str = ""
    llm_challenge: str | None = None
    code_challenge: str | None = None


class VisionDocument:
    def __init__(
        self,
        path: Path,
        title: str = "Projekt – Produktvision",
        vision_statement: str = "",
        target_audience: str = "",
        tech_stack: str = "",
        competitive_landscape: str = "",
        core_problems: str = "",
        features: list[VisionFeature] | None = None,
        tasks: list[VisionTask] | None = None,
    ) -> None:
        self.path = path
        self.title = title
        self.vision_statement = vision_statement
        self.target_audience = target_audience
        self.tech_stack = tech_stack
        self.competitive_landscape = competitive_landscape
        self.core_problems = core_problems
        self.features: list[VisionFeature] = features if features is not None else []
        self.tasks: list[VisionTask] = tasks if tasks is not None else []
        self._found_headings: set[str] = set()

    @classmethod
    def from_file(cls, path: Path) -> "VisionDocument":
        if not path.exists():
            raise VisionNotFoundError(f"vision.md nicht gefunden: {path}")
        return cls._parse(path, path.read_text())

    @classmethod
    def _parse(cls, path: Path, content: str) -> "VisionDocument":
        doc = cls(path=path)
        lines = content.splitlines()

        if lines and lines[0].startswith("# "):
            doc.title = lines[0][2:].strip()

        sections: dict[str, list[str]] = {}
        current: str | None = None
        for line in lines[1:]:
            if line.startswith("## "):
                current = line.strip()
                doc._found_headings.add(current)
                sections[current] = []
            elif current is not None:
                sections[current].append(line)

        def section_text(key: str) -> str:
            return "\n".join(sections[key]).strip() if key in sections else ""

        doc.vision_statement = section_text("## Vision")
        doc.target_audience = section_text("## Zielgruppe")
        doc.tech_stack = section_text("## Tech Stack")
        doc.competitive_landscape = section_text("## Competitive Landscape")
        doc.core_problems = section_text("## Kernprobleme")

        if "## Features" in sections:
            doc.features = _parse_features(sections["## Features"])
        if "## Tasks" in sections:
            doc.tasks = _parse_tasks(sections["## Tasks"])

        return doc

    def validate(self) -> bool:
        return all(h in self._found_headings for h in REQUIRED_HEADINGS)

    def add_feature(self, title: str, description: str = "") -> None:
        if not title.strip():
            raise ValueError("Titel darf nicht leer sein")
        self.features.append(VisionFeature(title=title.strip(), description=description.strip()))

    def add_task(self, title: str) -> None:
        if not title.strip():
            raise ValueError("Titel darf nicht leer sein")
        self.tasks.append(VisionTask(title=title.strip()))

    def save(self) -> None:
        self.path.write_text(self._serialize())

    def _serialize(self) -> str:
        parts: list[str] = [f"# {self.title}", ""]

        for heading, content in [
            ("## Vision", self.vision_statement),
            ("## Zielgruppe", self.target_audience),
            ("## Tech Stack", self.tech_stack),
            ("## Competitive Landscape", self.competitive_landscape),
            ("## Kernprobleme", self.core_problems),
        ]:
            parts += [heading, ""]
            if content:
                parts += [content, ""]

        parts += ["## Features", ""]
        for i, feature in enumerate(self.features, 1):
            line = f"{i}. **{feature.title}**"
            if feature.description:
                line += f" – {feature.description}"
            parts.append(line)
            if feature.llm_challenge is not None:
                parts.append(f"   > LLM Challenge: {feature.llm_challenge}")
            if feature.code_challenge is not None:
                parts.append(f"   > Code Challenge: {feature.code_challenge}")
            parts.append("")

        parts += ["## Tasks", ""]
        for task in self.tasks:
            checkbox = "x" if task.done else " "
            parts.append(f"- [{checkbox}] {task.title}")

        return "\n".join(parts) + "\n"


def _parse_features(lines: list[str]) -> list[VisionFeature]:
    features: list[VisionFeature] = []
    current: VisionFeature | None = None

    for line in lines:
        m = _FEATURE_RE.match(line)
        if m:
            if current is not None:
                features.append(current)
            current = VisionFeature(
                title=m.group(2),
                description=(m.group(3) or "").strip(),
            )
            continue

        bq = _BLOCKQUOTE_RE.match(line)
        if bq and current is not None:
            value = bq.group(2).strip()
            if bq.group(1) == "LLM Challenge":
                current.llm_challenge = value
            else:
                current.code_challenge = value

    if current is not None:
        features.append(current)
    return features


def _parse_tasks(lines: list[str]) -> list[VisionTask]:
    tasks: list[VisionTask] = []
    for line in lines:
        m = _TASK_RE.match(line)
        if m:
            tasks.append(VisionTask(title=m.group(2).strip(), done=m.group(1) == "x"))
    return tasks
