"""Regression Check: Stufe 1 (regelbasiert) + Stufe 2 (LLM-semantisch) für Specs (SPEC-0030)."""
from __future__ import annotations

import abc
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CheckFinding:
    spec_id: str
    section: str
    own_section: str
    type: str        # overlap / conflict / redundancy
    severity: str    # error / warning / info
    description: str
    source: str      # rule / llm

    def to_dict(self) -> dict:
        return {
            "spec_id": self.spec_id,
            "section": self.section,
            "own_section": self.own_section,
            "type": self.type,
            "severity": self.severity,
            "description": self.description,
            "source": self.source,
        }


@dataclass
class RegressionResult:
    spec_id: str
    findings: list[CheckFinding] = field(default_factory=list)
    llm_skipped: bool = False
    llm_skip_reason: str = ""


class RegressionCheckHandler(abc.ABC):
    def __init__(self, next_handler: "RegressionCheckHandler | None" = None) -> None:
        self._next = next_handler

    @abc.abstractmethod
    def handle(self, target: dict, context_specs: list[dict], result: RegressionResult) -> None:
        pass

    def _continue(self, target: dict, context_specs: list[dict], result: RegressionResult) -> None:
        if self._next:
            self._next.handle(target, context_specs, result)


class RuleBasedCheckHandler(RegressionCheckHandler):
    """Stufe 1: regelbasierte Prüfung auf Titel-, Endpoint- und FR-Konflikte."""

    _ENDPOINT_RE = re.compile(r"/api/[a-zA-Z0-9/_\-{}]+")

    def handle(self, target: dict, context_specs: list[dict], result: RegressionResult) -> None:
        target_title = (target.get("title") or "").lower().strip()
        target_body = target.get("_body", "")
        target_endpoints = set(self._ENDPOINT_RE.findall(target_body))

        for spec in context_specs:
            other_id = spec.get("id", "?")
            other_title = (spec.get("title") or "").lower().strip()
            other_body = spec.get("_body", "")

            if target_title and other_title and target_title == other_title:
                result.findings.append(CheckFinding(
                    spec_id=other_id,
                    section="title",
                    own_section="title",
                    type="redundancy",
                    severity="error",
                    description=f"Identischer Titel wie {other_id}: '{spec.get('title')}'",
                    source="rule",
                ))

            other_endpoints = set(self._ENDPOINT_RE.findall(other_body))
            for ep in target_endpoints & other_endpoints:
                result.findings.append(CheckFinding(
                    spec_id=other_id,
                    section=f"endpoint {ep}",
                    own_section=f"endpoint {ep}",
                    type="conflict",
                    severity="warning",
                    description=f"Endpoint '{ep}' auch in {other_id} definiert.",
                    source="rule",
                ))

        self._continue(target, context_specs, result)


class SemanticCheckStrategy(abc.ABC):
    @abc.abstractmethod
    def build_prompt(self, target: dict, context_specs: list[dict]) -> str:
        pass


class FullContentStrategy(SemanticCheckStrategy):
    """Vergleicht den vollständigen Spec-Text (default, FR-02)."""

    _MAX_SPEC_CHARS = 1200
    _MAX_CONTEXT_SPECS = 15

    def build_prompt(self, target: dict, context_specs: list[dict]) -> str:
        target_body = (target.get("_body") or "")[:3000]
        target_id = target.get("id", "?")
        target_title = target.get("title", "")

        summaries = [
            f"=== {s.get('id')} – {s.get('title', '')} ===\n"
            f"{(s.get('_body') or '')[:self._MAX_SPEC_CHARS]}"
            for s in context_specs[: self._MAX_CONTEXT_SPECS]
        ]
        context_text = "\n\n".join(summaries) if summaries else "(keine bestehenden Specs)"

        return (
            f"Analysiere semantische Überschneidungen zwischen einer neuen Spec und "
            f"bestehenden, implementierten Specs.\n\n"
            f"## Ziel-Spec: {target_id} – {target_title}\n{target_body}\n\n"
            f"## Bestehende Specs (implementiert / in-progress):\n{context_text}\n\n"
            f"Suche nach inhaltlichen Überschneidungen: Abschnitte die dasselbe Problem "
            f"doppelt lösen, auch wenn unterschiedliche Feldnamen oder Endpoints genutzt werden.\n\n"
            f"Antworte ausschließlich als JSON-Array:\n"
            f'[{{"spec_id": "SPEC-XXXX", "section": "FR-NN", "own_section": "FR-NN", '
            f'"type": "overlap|conflict|redundancy", "severity": "error|warning|info", '
            f'"description": "ein konkreter Satz"}}]\n\n'
            f"Bei keinen Überschneidungen: antworte mit []"
        )


class LLMSemanticCheckHandler(RegressionCheckHandler):
    """Stufe 2: LLM-basierter Semantik-Check (FR-01–FR-03, FR-06)."""

    def __init__(
        self,
        provider: Any,
        strategy: SemanticCheckStrategy | None = None,
        next_handler: "RegressionCheckHandler | None" = None,
    ) -> None:
        super().__init__(next_handler)
        self._provider = provider
        self._strategy = strategy or FullContentStrategy()

    def handle(self, target: dict, context_specs: list[dict], result: RegressionResult) -> None:
        if self._provider is None:
            result.llm_skipped = True
            result.llm_skip_reason = "kein API-Zugang"
            self._continue(target, context_specs, result)
            return

        prompt = self._strategy.build_prompt(target, context_specs)
        try:
            response = self._provider.complete(prompt, max_tokens=2048)
            raw_text = response.text if hasattr(response, "text") else str(response)
            match = re.search(r"\[.*\]", raw_text, re.DOTALL)
            if match:
                for item in json.loads(match.group(0)):
                    if not isinstance(item, dict):
                        continue
                    result.findings.append(CheckFinding(
                        spec_id=item.get("spec_id", "?"),
                        section=item.get("section", ""),
                        own_section=item.get("own_section", ""),
                        type=item.get("type", "overlap"),
                        severity=item.get("severity", "warning"),
                        description=item.get("description", ""),
                        source="llm",
                    ))
        except Exception as exc:
            result.llm_skipped = True
            result.llm_skip_reason = str(exc)[:120]

        self._continue(target, context_specs, result)


class RegressionCheckChain:
    """Verwaltet die Chain of Responsibility für Regression Checks."""

    def __init__(self, repo_root: Path) -> None:
        self._repo_root = Path(repo_root)

    def _load_specs(self, statuses: tuple[str, ...]) -> list[dict]:
        specs_dir = self._repo_root / ".sdd" / "specs"
        if not specs_dir.exists():
            return []
        result = []
        for md in sorted(specs_dir.glob("*.md")):
            try:
                from .frontmatter import parse
                doc = parse(md)
                if doc.frontmatter.get("status") in statuses:
                    data = dict(doc.frontmatter)
                    data["_body"] = doc.body
                    result.append(data)
            except Exception:
                pass
        return result

    def _load_target(self, spec_id: str) -> dict | None:
        specs_dir = self._repo_root / ".sdd" / "specs"
        if not specs_dir.exists():
            return None
        from .frontmatter import parse
        for md in specs_dir.glob("*.md"):
            try:
                doc = parse(md)
                if doc.frontmatter.get("id") == spec_id:
                    data = dict(doc.frontmatter)
                    data["_body"] = doc.body
                    return data
            except Exception:
                pass
        return None

    def run(
        self,
        spec_id: str,
        provider: Any = None,
        strategy: SemanticCheckStrategy | None = None,
    ) -> RegressionResult:
        result = RegressionResult(spec_id=spec_id)

        target = self._load_target(spec_id)
        if target is None:
            return result

        context_specs = [
            s for s in self._load_specs(("implemented", "in-progress"))
            if s.get("id") != spec_id
        ]

        llm_handler = LLMSemanticCheckHandler(provider=provider, strategy=strategy)
        rule_handler = RuleBasedCheckHandler(next_handler=llm_handler)
        rule_handler.handle(target, context_specs, result)

        return result
