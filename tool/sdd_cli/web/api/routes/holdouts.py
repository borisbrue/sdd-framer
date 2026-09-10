"""Holdout-Status API – SPEC-0043.

GET /api/holdouts/{spec_id}        — Neuester Holdout-Lauf (Status + Szenarien)
GET /api/holdouts/{spec_id}/stream — SSE-Stream für Status-Updates (FR-01, FR-04)
"""
from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse

sys.path.insert(0, str(Path(__file__).parents[3]))
sys.path.insert(0, str(Path(__file__).parents[1]))

router = APIRouter()

_SPEC_ID_RE = re.compile(r"^[A-Z]+-\d{4}$")


def _check_spec_id(spec_id: str) -> JSONResponse | None:
    if not _SPEC_ID_RE.match(spec_id):
        return JSONResponse(
            status_code=422,
            content={"code": "INVALID_SPEC_ID", "message": f"Ungültige Spec-ID: {spec_id}"},
        )
    return None


def _spec_exists(root: Path, spec_id: str) -> bool:
    return any((root / ".sdd" / "specs").glob(f"{spec_id}-*.md"))


def _get_hol_ids_for_spec(root: Path, spec_id: str) -> set[str]:
    """Collects all HOL-IDs from holdout files that belong to spec_id."""
    hol_ids: set[str] = set()
    holdout_dir = root / ".sdd" / "holdout"
    if not holdout_dir.exists():
        return hol_ids
    for path in holdout_dir.glob("*.md"):
        try:
            text = path.read_text()
            if f"\nspec: {spec_id}" in text or f"\nspec: {spec_id}\n" in text:
                hol_id = path.stem.split("-")[0] + "-" + path.stem.split("-")[1]
                hol_ids.add(hol_id)
        except Exception:
            continue
    return hol_ids


def get_holdout_status(spec_id: str) -> dict[str, Any] | None:
    """Gibt den Status des neuesten Holdout-Laufs zurück.

    Returns None when the spec does not exist (→ 404).
    Returns {status: "none"} when spec exists but has no evaluation runs.
    """
    try:
        import sdd_context
        config = sdd_context.get_config()
        root = Path(config.root)
    except Exception:
        root = Path(".")

    if not _spec_exists(root, spec_id):
        return None  # spec unknown → 404

    hol_ids = _get_hol_ids_for_spec(root, spec_id)
    if not hol_ids:
        return _none_response(spec_id)

    evals_dir = root / ".sdd" / "evaluations"
    if not evals_dir.exists():
        return _none_response(spec_id)

    best: dict | None = None
    best_ts = ""
    for path in evals_dir.glob("*.json"):
        try:
            data = json.loads(path.read_text())
            eval_hol_ids = {s["hol_id"] for s in data.get("scenarios", [])}
            if eval_hol_ids & hol_ids:  # this eval covers at least one of our holdouts
                ts = data.get("timestamp", "")
                if ts > best_ts:
                    best_ts = ts
                    best = data
        except Exception:
            continue

    if best is None:
        return _none_response(spec_id)

    return _build_response(best, spec_id, hol_ids)


def _none_response(spec_id: str) -> dict[str, Any]:
    import datetime
    return {
        "spec_id": spec_id,
        "status": "none",
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "run_id": None,
        "scenarios": [],
    }


def _build_response(data: dict, spec_id: str, hol_ids: set[str]) -> dict[str, Any]:
    relevant = [s for s in data.get("scenarios", []) if s.get("hol_id") in hol_ids]

    if not relevant:
        return _none_response(spec_id)

    all_passed = all(s.get("passed", False) for s in relevant)
    any_failed = any(not s.get("passed", True) for s in relevant)

    if all_passed:
        raw_status = "passed"
    elif any_failed:
        raw_status = "failed"
    else:
        raw_status = "none"

    failed_scenarios = [
        {
            "name": s.get("title", s.get("hol_id", "?")),
            "status": "failed",
            "error_message": s.get("error", ""),
        }
        for s in relevant
        if not s.get("passed", True)
    ]

    return {
        "spec_id": spec_id,
        "status": raw_status,
        "updated_at": data.get("timestamp", data.get("updated_at", "")),
        "run_id": data.get("run_id", data.get("timestamp")),
        "scenarios": failed_scenarios if raw_status == "failed" else [],
    }


def stream_holdout_status(spec_id: str) -> Iterator[str]:
    """Liefert einen SSE-Event-Generator für den Holdout-Status."""
    result = get_holdout_status(spec_id)
    if result is not None:
        yield f"data: {json.dumps(result)}\n\n"
    yield "event: done\ndata: \n\n"


@router.get("/holdouts/{spec_id}", summary="Holdout-Status (SPEC-0043 FR-04)")
def get_holdout_status_endpoint(spec_id: str) -> Any:
    invalid = _check_spec_id(spec_id)
    if invalid:
        return invalid
    result = get_holdout_status(spec_id)
    if result is None:
        return JSONResponse(
            status_code=404,
            content={"code": "NOT_FOUND", "message": f"Kein Holdout-Lauf für {spec_id}"},
        )
    return result


@router.get("/holdouts/{spec_id}/stream", summary="Holdout-Status SSE-Stream (SPEC-0043 FR-01)")
def stream_holdout_status_endpoint(spec_id: str) -> Any:
    invalid = _check_spec_id(spec_id)
    if invalid:
        return invalid
    try:
        generator = stream_holdout_status(spec_id)
    except KeyError as exc:
        return JSONResponse(
            status_code=404,
            content={"code": "NOT_FOUND", "message": str(exc)},
        )
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
