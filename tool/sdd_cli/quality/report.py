"""Report nach `quality-report.schema.json` (SPEC-0054 FR-12, CON-0195)."""
from __future__ import annotations

from datetime import datetime, timezone

from .score import ScoreNode


def build_report(*, tree: ScoreNode, git_sha: str | None, duration_ms: int,
                 spec_id: str | None, base_ref: str | None, frs: list[dict],
                 holdout_rate: float | None, test_run: str | None, architecture: dict,
                 probes: list[dict], gates: list[dict] | None, excluded: int) -> dict:
    baum = tree.to_dict()
    report: dict = {
        "schema_version": 1,
        "git_sha": git_sha or "0000000",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "duration_ms": duration_ms,
        "incomplete": tree.incomplete(),
        "score": baum["score"],
        "tree": baum,
        "requirements": {"frs": frs, "holdout_pass_rate": holdout_rate},
        "architecture": architecture,
        "probes": probes,
        "excluded_findings": excluded,
    }
    if spec_id:
        report["spec"] = spec_id
    if base_ref:
        report["base_ref"] = base_ref
    if test_run:
        report["requirements"]["test_run"] = test_run
    if gates is not None:
        report["gates"] = gates
    return report
