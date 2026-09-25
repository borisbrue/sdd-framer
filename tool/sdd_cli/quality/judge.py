"""Optionaler LLM-Judge mit versionierter Rubrik (SPEC-0054 FR-09).

Der Judge fließt nur mit `quality.weights.judge > 0` in den Gesamtscore ein; Modell und
Rubrikversion stehen im Report.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from ..frontmatter import parse_safe
from .score import MetricLeaf, ScoreNode

RUBRIC_FILE = Path(".sdd") / "roles" / "judge.md"
DEFAULT_RUBRIC_VERSION = "builtin-1"
DEFAULT_RUBRIC = """Bewerte den folgenden Diff nach vier Kriterien, jeweils 1 (schlecht) bis 5 (sehr gut):
- lesbarkeit: 1 = Namen und Struktur verschleiern die Absicht; 5 = liest sich ohne Kommentar.
- idiomatik: 1 = gegen die Konventionen der Sprache; 5 = so, wie erfahrene Entwickler es schreiben.
- passung: 1 = ignoriert die Muster des bestehenden Codes; 5 = fügt sich nahtlos ein.
- fehlerbehandlung: 1 = Fehler werden verschluckt; 5 = Fehler werden gezielt behandelt und gemeldet.
"""
ANSWER_FORMAT = ('Antworte ausschließlich mit JSON: {"scores": {"<kriterium>": <1-5>, ...}, '
                 '"begruendung": "<ein Satz>"}')
_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)
MAX_DIFF_CHARS = 60_000


def load_rubric(root: Path) -> tuple[str, str]:
    pfad = root / RUBRIC_FILE
    doc = parse_safe(pfad) if pfad.is_file() else None
    if doc is None:
        return DEFAULT_RUBRIC, DEFAULT_RUBRIC_VERSION
    return doc.body.strip(), str(doc.frontmatter.get("version") or "unversioniert")


def _na(weight: float, model: str, version: str, reason: str) -> ScoreNode:
    return ScoreNode("judge", weight, [MetricLeaf("rubric", None, None, reason=reason)],
                     extra={"model": model, "rubric_version": version})


def judge_node(root: Path, diff: str, provider, model: str, *, weight: float) -> ScoreNode:
    rubrik, version = load_rubric(root)
    if not diff.strip():
        return _na(weight, model, version, "kein Diff")
    prompt = f"{rubrik}\n\n{ANSWER_FORMAT}\n\n```diff\n{diff[:MAX_DIFF_CHARS]}\n```"
    try:
        text = provider.complete(prompt, max_tokens=1024).text
        daten = json.loads(_JSON_RE.search(text).group(0))
        werte = {str(k): int(v) for k, v in daten["scores"].items()}
        if not werte or any(not 1 <= v <= 5 for v in werte.values()):
            raise ValueError("Werte außerhalb 1–5")
    except Exception as exc:
        return _na(weight, model, version, f"Antwort nicht auswertbar: {exc}")
    leaves = [MetricLeaf(re.sub(r"[^a-z0-9_]", "_", k.lower()), float(v), (v - 1) / 4,
                         good=5, bad=1) for k, v in werte.items()]
    return ScoreNode("judge", weight, leaves, extra={"model": model, "rubric_version": version})
