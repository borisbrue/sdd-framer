"""GET /api/patterns – akzeptierte Patterns mit Code-Fundstellen (SPEC-0049, CON-0184)."""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi import APIRouter

sys.path.insert(0, str(Path(__file__).parents[1]))
from sdd_context import get_config

from sdd_cli.pattern_usage import PatternUsageService

router = APIRouter()


@router.get("/patterns")
def get_patterns() -> list[dict]:
    cfg = get_config()
    raw = getattr(cfg, "raw", {}) or {}
    roots_cfg = (raw.get("patterns") or {}).get("scan_roots")
    scan_roots = [cfg.root / r for r in roots_cfg] if roots_cfg else None
    service = PatternUsageService(root=cfg.root, scan_roots=scan_roots)
    return [usage.to_dict() for usage in service.usage()]
