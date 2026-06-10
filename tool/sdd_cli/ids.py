"""Vergabe und Erkennung von eindeutigen IDs (SPEC, CON, TST)."""
from __future__ import annotations

from pathlib import Path
import re

from .config import SddConfig
from .frontmatter import parse_safe


KINDS = {
    "spec":     "spec_prefix",
    "contract": "contract_prefix",
    "test":     "test_prefix",
    "project":  "project_prefix",
    "holdout":  "holdout_prefix",
}


def search_dirs(config: SddConfig, kind: str) -> list[Path]:
    """Verzeichnisse, in denen Dokumente einer Art liegen können."""
    if kind == "spec":
        return [config.specs_dir]
    if kind == "contract":
        return [config.contracts_dir]
    if kind == "test":
        return config.all_test_dirs
    if kind == "project":
        return [config.projects_dir]
    if kind == "holdout":
        return [config.holdout_dir]
    raise ValueError(f"Unbekannte Art: {kind}")


def existing_ids(config: SddConfig, kind: str) -> set[str]:
    """Sammelt alle bereits vergebenen IDs der gegebenen Art."""
    prefix = config.prefix(kind)
    pattern = re.compile(rf"^{prefix}-\d+$")
    found: set[str] = set()
    for base in search_dirs(config, kind):
        if not base.exists():
            continue
        for md in base.rglob("*.md"):
            doc = parse_safe(md)
            if doc and isinstance(doc.frontmatter.get("id"), str):
                if pattern.match(doc.frontmatter["id"]):
                    found.add(doc.frontmatter["id"])
    return found


def next_id(config: SddConfig, kind: str) -> str:
    """Nächste freie ID für die gegebene Art."""
    prefix = config.prefix(kind)
    padding = config.id_padding()
    used = existing_ids(config, kind)
    numbers = [int(i.split("-")[1]) for i in used]
    nxt = (max(numbers) + 1) if numbers else 1
    return f"{prefix}-{str(nxt).zfill(padding)}"
