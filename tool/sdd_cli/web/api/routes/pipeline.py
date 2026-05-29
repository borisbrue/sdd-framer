"""Pipeline-State Endpoint – berechnet den aktuellen Stand einer Spec im SDD-Workflow."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

import sys
sys.path.insert(0, str(Path(__file__).parents[1]))


def _enriched_env() -> dict[str, str]:
    """Return os.environ enriched with common tool dirs so subprocesses find binaries."""
    extra_dirs = [
        str(Path.home() / ".local/bin"),
        str(Path(sys.executable).parent),
        str(Path.home() / ".local/share/uv/tools/sdd-framer/bin"),
        str(Path.home() / ".local/share/uv/tools/sdd-cli/bin"),
        str(Path.home() / ".var/app/com.visualstudio.code/data/uv/tools/sdd-framer/bin"),
        str(Path.home() / ".var/app/com.visualstudio.code/data/python/bin"),
    ]
    env = os.environ.copy()
    existing = env.get("PATH", "")
    env["PATH"] = ":".join(extra_dirs) + (":" + existing if existing else "")
    return env


def _find_sdd() -> str:
    """Locate the sdd CLI binary regardless of subprocess PATH."""
    candidates = [
        Path(sys.executable).parent / "sdd",
        Path.home() / ".local/share/uv/tools/sdd-framer/bin/sdd",
        Path.home() / ".local/share/uv/tools/sdd-cli/bin/sdd",
        Path.home() / ".var/app/com.visualstudio.code/data/uv/tools/sdd-framer/bin/sdd",
        Path.home() / ".var/app/com.visualstudio.code/data/python/bin/sdd",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return "sdd"
from sdd_context import get_config, get_log_streamer
from sdd_cli.frontmatter import parse_safe
from sdd_cli.dev_container import container_name, get_runtime

router = APIRouter()


def _container_running(spec_id: str) -> bool:
    try:
        cfg = get_config()
        runtime = get_runtime(cfg)
        return runtime.inspect_status(container_name(spec_id)) == "running"
    except Exception:
        return False


def _holdout_count(spec_id: str) -> int:
    try:
        cfg = get_config()
        holdout_dir = cfg.holdout_dir
        if not holdout_dir.exists():
            return 0
        count = 0
        for f in holdout_dir.glob("HOL-*.md"):
            doc = parse_safe(f)
            if doc and doc.frontmatter.get("spec") == spec_id:
                count += 1
        return count
    except Exception:
        return 0


def _last_test_result(spec_id: str) -> dict[str, Any] | None:
    try:
        cfg = get_config()
        results_dir = cfg.sdd_dir / "test-results"
        if not results_dir.exists():
            return None
        files = sorted(results_dir.glob(f"{spec_id}-*.json"), reverse=True)
        if not files:
            return None
        import json
        return json.loads(files[0].read_text())
    except Exception:
        return None


def _last_evaluation(spec_id: str) -> dict[str, Any] | None:
    try:
        cfg = get_config()
        evals_dir = cfg.sdd_dir / "evaluations"
        if not evals_dir.exists():
            return None
        files = sorted(evals_dir.glob("*.json"), reverse=True)
        for f in files:
            import json
            data = json.loads(f.read_text())
            if data.get("spec_id") == spec_id or spec_id in str(f):
                return data
        # Fallback: return most recent evaluation
        if files:
            import json
            return json.loads(files[0].read_text())
        return None
    except Exception:
        return None


def _pr_exists(spec_id: str) -> str | None:
    try:
        cfg = get_config()
        pr_file = cfg.sdd_dir / "prs" / f"PR-{spec_id}.md"
        if pr_file.exists():
            return str(pr_file.relative_to(cfg.root))
        return None
    except Exception:
        return None


# ── Stage helpers ──────────────────────────────────────────────────────────────

_DONE = "done"
_ACTIVE = "active"
_PENDING = "pending"
_FAILED = "failed"
_SKIPPED = "skipped"


def _stage(id_: str, label: str, status: str, **kwargs) -> dict[str, Any]:
    return {"id": id_, "label": label, "status": status, **kwargs}


def _compute_pipeline(spec_id: str) -> dict[str, Any]:
    cfg = get_config()

    # ── Load spec ──────────────────────────────────────────────────────────────
    spec_doc = None
    for md in cfg.specs_dir.rglob("*.md"):
        doc = parse_safe(md)
        if doc and doc.frontmatter.get("id") == spec_id:
            spec_doc = doc
            break
    if spec_doc is None:
        raise HTTPException(404, f"Spec {spec_id} nicht gefunden")

    fm = spec_doc.frontmatter
    status = fm.get("status", "draft")
    contract_ids: list[str] = fm.get("contracts") or []

    # ── Count contract statuses ────────────────────────────────────────────────
    contracts_approved = 0
    contracts_total = len(contract_ids)
    for cid in contract_ids:
        for md in cfg.contracts_dir.rglob("*.md"):
            doc = parse_safe(md)
            if doc and doc.frontmatter.get("id") == cid:
                if doc.frontmatter.get("status") == "approved":
                    contracts_approved += 1
                break

    # ── Gate state ─────────────────────────────────────────────────────────────
    import json as _json
    _gate_file = cfg.sdd_dir / "pipeline" / f"{spec_id}-gate.json"
    _gate_data = _json.loads(_gate_file.read_text()) if _gate_file.exists() else {}
    _phase_history: dict[str, Any] = {
        e["phase"]: e for e in _gate_data.get("phase_history", [])
    }

    def _phase_done(phase: str) -> bool:
        return _phase_history.get(phase, {}).get("result") == "ok"

    # ── Derived facts ──────────────────────────────────────────────────────────
    container_up = _container_running(spec_id)
    holdout_count = _holdout_count(spec_id)
    last_test = _last_test_result(spec_id)
    last_eval = _last_evaluation(spec_id)
    pr_path = _pr_exists(spec_id)

    tests_green = (
        last_test is not None
        and last_test.get("passed", 0) > 0
        and last_test.get("passed") == last_test.get("total")
    ) if last_test else False

    eval_passed = (
        last_eval is not None and last_eval.get("pass_rate", 0) >= 0.9
    ) if last_eval else False

    eval_rate = last_eval.get("pass_rate") if last_eval else None

    # ── Status predicates ──────────────────────────────────────────────────────
    is_draft     = status == "draft"
    is_review    = status == "review"
    is_approved  = status == "approved"
    is_progress  = status == "in-progress"
    is_eval_fail = status == "evaluation-failed"
    is_done      = status == "implemented"

    past_approved  = is_approved or is_progress or is_eval_fail or is_done
    past_progress  = is_progress or is_eval_fail or is_done

    # ── Build stages ───────────────────────────────────────────────────────────
    stages: list[dict[str, Any]] = []

    # 1. Spec-Erstellung (Gate-Phasen als Substeps)
    _gp = _phase_done  # shorthand
    _gate_phases = [
        ("spec-draft",         "Draft abschließen",     "/api/specs/{}/gate-spec-draft"),
        ("spec-review",        "Spec Review (KI)",      "/api/specs/{}/review"),
        ("contracts-proposed", "Contracts vorschlagen", "/api/specs/{}/propose-contracts"),
        ("contracts-review",   "Contract-Review",       "/api/gate/{}/contract-review"),
        ("tests-generated",    "Tests generieren",      "/api/gate/{}/test-generate"),
        ("spec-approved",      "Freigeben",             "/api/gate/{}/approve"),
    ]
    _gate_substeps = []
    _gate_next_action: dict[str, Any] | None = None
    for phase_key, phase_label, phase_ep in _gate_phases:
        if _gp(phase_key):
            sub_status = _DONE
        elif past_approved:
            sub_status = _DONE
        elif _gate_next_action is None:
            sub_status = _ACTIVE
            _gate_next_action = {
                "id": phase_key, "label": phase_label,
                "endpoint": phase_ep.format(spec_id), "method": "POST",
            }
        else:
            sub_status = _PENDING
        _gate_substeps.append({"id": phase_key, "label": phase_label, "status": sub_status})

    spec_status = _DONE if past_approved else _ACTIVE
    stages.append(_stage("spec", "Spec", spec_status,
        detail=f"Status: {status}",
        substeps=_gate_substeps,
        actions=[] if past_approved else (
            [_gate_next_action] if _gate_next_action else
            [{"id": "gate-check", "label": "Gate prüfen", "endpoint": f"/api/specs/{spec_id}/gate-check", "method": "POST"}]
        ),
    ))

    # 2. Contracts
    if contracts_total == 0:
        con_status = _PENDING if is_draft else _ACTIVE
        con_detail = "Keine Contracts verknüpft"
    elif contracts_approved == contracts_total:
        con_status = _DONE
        con_detail = f"{contracts_total} Contract{'s' if contracts_total != 1 else ''}, alle approved"
    else:
        con_status = _ACTIVE if (is_draft or is_review) else _DONE
        con_detail = f"{contracts_approved}/{contracts_total} approved"
    stages.append(_stage("contracts", "Contracts", con_status, detail=con_detail, count=contracts_total))

    # 3. Holdout-Szenarien
    if is_done or eval_passed:
        hol_status = _DONE
    elif holdout_count > 0:
        hol_status = _DONE
    elif past_approved:
        hol_status = _ACTIVE
    else:
        hol_status = _PENDING
    hol_actions = []
    if hol_status == _ACTIVE and holdout_count == 0:
        hol_actions = [{"id": "generate-holdouts", "label": "Holdouts generieren (KI)",
                        "endpoint": f"/api/specs/{spec_id}/generate-holdouts", "method": "POST"}]
    elif hol_status == _DONE and past_approved:
        hol_actions = [{"id": "regen-holdouts", "label": "Holdouts neu generieren",
                        "endpoint": f"/api/specs/{spec_id}/generate-holdouts", "method": "POST",
                        "secondary": True}]
    stages.append(_stage("holdouts", "Holdout-Szenarien", hol_status,
        detail=f"{holdout_count} Szenario{'s' if holdout_count != 1 else ''}" if holdout_count else "Noch keine Szenarien",
        count=holdout_count,
        actions=hol_actions,
    ))

    # 4. Implementierung
    if is_done:
        impl_status = _DONE
    elif is_eval_fail:
        impl_status = _DONE
    elif is_progress:
        impl_status = _ACTIVE
    elif past_approved:
        impl_status = _ACTIVE
    else:
        impl_status = _PENDING

    impl_actions = []
    if (is_approved or is_progress) and not container_up and not tests_green and not is_done and not is_eval_fail:
        impl_actions = [{"id": "start", "label": "Container starten", "endpoint": f"/api/specs/{spec_id}/start", "method": "POST"}]
    elif is_progress and container_up:
        impl_actions = [
            {"id": "run-tests", "label": "Tests im Container", "endpoint": f"/api/specs/{spec_id}/run-tests", "method": "POST"},
            {"id": "finalize", "label": "Finalize + PR", "endpoint": f"/api/specs/{spec_id}/finalize", "method": "POST", "secondary": True},
        ]

    stages.append(_stage("implementation", "Implementierung", impl_status,
        substeps=[
            {"id": "container", "label": "Container",
             "status": _DONE if container_up or is_eval_fail or is_done else (_ACTIVE if is_progress else _PENDING),
             "detail": "läuft" if container_up else None},
            {"id": "tdd",       "label": "Tests grün",
             "status": _DONE if tests_green or is_eval_fail or is_done else (_ACTIVE if is_progress else _PENDING),
             "detail": f"{last_test.get('passed')}/{last_test.get('total')} passed" if last_test else None},
            {"id": "finalize",  "label": "Finalize + PR",
             "status": _DONE if pr_path or is_eval_fail or is_done else _PENDING,
             "detail": pr_path},
        ],
        actions=impl_actions,
    ))

    # 5. Evaluation
    if is_done and eval_passed:
        eval_status = _DONE
    elif is_eval_fail:
        eval_status = _FAILED
    elif last_eval and eval_passed:
        eval_status = _DONE
    elif past_progress:
        eval_status = _ACTIVE if (pr_path or is_eval_fail) else _PENDING
    else:
        eval_status = _PENDING

    eval_detail = None
    if eval_rate is not None:
        eval_detail = f"Pass-Rate: {eval_rate:.0%}"
    elif is_eval_fail:
        eval_detail = "3 Versuche fehlgeschlagen"

    stages.append(_stage("evaluation", "Holdout-Evaluation", eval_status,
        detail=eval_detail,
        pass_rate=eval_rate,
        actions=[{"id": "evaluate", "label": "sdd evaluate", "endpoint": f"/api/specs/{spec_id}/evaluate", "method": "POST"}]
            if eval_status == _ACTIVE else [],
    ))

    # 6. Implementiert
    stages.append(_stage("done", "Implementiert", _DONE if is_done else _PENDING))

    # ── Next action ────────────────────────────────────────────────────────────
    next_action = None
    if (is_draft or is_review) and _gate_next_action:
        next_action = _gate_next_action
    elif is_draft or is_review:
        next_action = {"label": "Gate prüfen", "endpoint": f"/api/specs/{spec_id}/gate-check", "method": "POST"}
    elif is_approved and not container_up:
        next_action = {"label": f"sdd start {spec_id}", "command": "start", "endpoint": f"/api/specs/{spec_id}/start", "method": "POST"}
    elif is_progress and not container_up and not tests_green:
        next_action = {"label": "Container starten", "command": "start", "endpoint": f"/api/specs/{spec_id}/start", "method": "POST"}
    elif is_progress and not tests_green:
        next_action = {"label": f"/sdd-implement {spec_id}", "command": "implement", "info": True}
    elif is_progress and tests_green and not pr_path:
        next_action = {"label": f"sdd finalize {spec_id}", "command": "finalize", "endpoint": f"/api/specs/{spec_id}/finalize", "method": "POST"}
    elif (is_progress or pr_path) and not eval_passed and not is_eval_fail:
        next_action = {"label": f"sdd evaluate {spec_id}", "command": "evaluate", "endpoint": f"/api/specs/{spec_id}/evaluate", "method": "POST"}
    elif is_eval_fail:
        next_action = {"label": "Spec überarbeiten oder Holdouts anpassen", "command": "review", "info": True}
    elif is_done:
        next_action = None

    return {
        "spec_id": spec_id,
        "status": status,
        "stages": stages,
        "next_action": next_action,
        "container_running": container_up,
        "holdout_count": holdout_count,
        "pr_path": pr_path,
    }


@router.get("/specs/{spec_id}/pipeline")
def get_pipeline(spec_id: str) -> dict[str, Any]:
    return _compute_pipeline(spec_id)


@router.post("/specs/{spec_id}/start")
def trigger_start(spec_id: str) -> dict[str, Any]:
    cfg = get_config()

    # Determine current spec status
    spec_status = None
    for md in cfg.specs_dir.rglob("*.md"):
        doc = parse_safe(md)
        if doc and doc.frontmatter.get("id") == spec_id:
            spec_status = doc.frontmatter.get("status")
            break

    env = _enriched_env()
    # Patch PATH persistently so ContainerRuntime._cmd and LogStreamer threads find podman/docker
    os.environ["PATH"] = env["PATH"]

    # If already in-progress, try to reuse or recreate the container
    if spec_status == "in-progress":
        try:
            runtime = get_runtime(cfg)
            cname = container_name(spec_id)
            status = runtime.inspect_status(cname)
            if status == "running":
                _attach_logs(spec_id, cname)
                return {"ok": True, "output": f"Container {cname} läuft — Log-Stream gestartet."}
            if status is not None:
                # Container exists but is stopped — just start it
                runtime.start(cname)
                _attach_logs(spec_id, cname)
                return {"ok": True, "output": f"Container {cname} gestartet."}
            # Container is gone — reset status to approved so sdd start can recreate it
            _patch_spec_status(cfg, spec_id, "approved")
        except Exception as e:
            return {"ok": False, "output": f"Container-Start fehlgeschlagen: {e}"}

    sdd = _find_sdd()
    result = subprocess.run(
        [sdd, "start", spec_id],
        capture_output=True, text=True,
        cwd=str(cfg.root),
        env=env,
    )
    if result.returncode == 0:
        cname = container_name(spec_id)
        _attach_logs(spec_id, cname)
    return {"ok": result.returncode == 0, "output": (result.stdout + result.stderr).strip()}


def _patch_spec_status(cfg, spec_id: str, status: str) -> None:
    for md in cfg.specs_dir.rglob("*.md"):
        doc = parse_safe(md)
        if doc and doc.frontmatter.get("id") == spec_id:
            doc.frontmatter["status"] = status
            doc.write()
            return


def _attach_logs(spec_id: str, cname: str) -> None:
    try:
        get_log_streamer().attach(spec_id, cname)
    except Exception:
        pass


@router.post("/specs/{spec_id}/finalize")
def trigger_finalize(spec_id: str) -> dict[str, Any]:
    cfg = get_config()
    sdd = _find_sdd()
    result = subprocess.run(
        [sdd, "finalize", spec_id, "--no-commit"],
        capture_output=True, text=True,
        cwd=str(cfg.root),
    )
    return {"ok": result.returncode == 0, "output": (result.stdout + result.stderr).strip()}


@router.post("/specs/{spec_id}/evaluate")
def trigger_evaluate(spec_id: str) -> dict[str, Any]:
    import threading

    cfg = get_config()
    base_url = (cfg.raw.get("evaluator", {}).get("base_url", "")
                or cfg.raw.get("evaluator_base_url", "")).strip()
    if not base_url:
        return {"ok": False, "output": "Kein evaluator_base_url konfiguriert. Bitte in den Einstellungen setzen."}

    bus = None
    try:
        bus = sdd_context.get_log_event_bus()
    except Exception:
        pass

    if bus is not None:
        try:
            bus.clear_buffer(spec_id)
        except Exception:
            pass
        bus.mark_active(spec_id)
        bus.publish(spec_id, f"━━━ sdd evaluate {spec_id} ━━━")
        bus.publish(spec_id, f"  Ziel: {base_url}")

    sdd = _find_sdd()
    env = _enriched_env()
    cwd = str(cfg.root)

    def _run_in_background() -> None:
        proc = subprocess.Popen(
            [sdd, "evaluate", "--base-url", base_url, "--spec", spec_id],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, cwd=cwd, env=env,
        )
        for line in proc.stdout:  # type: ignore[union-attr]
            stripped = line.rstrip("\n")
            if bus and stripped:
                try:
                    bus.publish(spec_id, stripped)
                except Exception:
                    pass
        proc.wait()
        if bus:
            ok = proc.returncode == 0
            try:
                bus.publish(spec_id, f"━━━ evaluate {'✓ PASS' if ok else '✗ FAIL'} (exit {proc.returncode}) ━━━")
            except Exception:
                pass

    threading.Thread(target=_run_in_background, daemon=True,
                     name=f"evaluate-{spec_id}").start()

    return {"ok": True, "output": "Evaluator gestartet – Logs im LogView."}


@router.post("/specs/{spec_id}/gate-spec-draft")
def trigger_gate_spec_draft(spec_id: str) -> dict[str, Any]:
    try:
        from sdd_cli.gate import ExecutionGate
        cfg = get_config()
        g = ExecutionGate(cfg.root)
        g.mark_phase_started(spec_id, "spec-draft")
        g.mark_phase_complete(spec_id, "spec-draft")
        return {"ok": True, "output": "spec-draft abgeschlossen"}
    except Exception as e:
        return {"ok": False, "output": str(e)}


@router.post("/specs/{spec_id}/gate-check")
def trigger_gate_check(spec_id: str) -> dict[str, Any]:
    try:
        from sdd_cli.gate import ExecutionGate
        cfg = get_config()
        result = ExecutionGate(cfg.root).check(spec_id)
        return {"ok": not result.blocked, "output": result.message}
    except Exception as e:
        return {"ok": False, "output": str(e)}
