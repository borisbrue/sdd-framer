"""Pre-Commit-Hook — Status-Check und blockierendes Regressions-Gate.

Zwei Aufgaben, in dieser Reihenfolge:

1. Status-Check (SPEC-0010 FR-02, CON-0167): inhaltlich geänderte Specs und
   Contracts fallen von approved/implemented zurück auf review. `sdd status-check`
   ist seit SPEC-0044 kein öffentlicher Befehl mehr, die Logik muss laut CON-0167
   aber weiterhin im Hook laufen ("status-check intern lauffähig").
2. Regressions-Gate (SPEC-0041 FR-08, CON-0155): liest git diff --cached, prüft
   ob main.py/routes/*.py/App.tsx betroffen sind, ermittelt betroffene Spec-IDs
   und führt deren Tests aus.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


_TRIGGER_PATTERNS = [
    re.compile(r"(^|/)main\.py$"),
    re.compile(r"/routes/[^/]+\.py$"),
    re.compile(r"(^|/)App\.tsx$"),
]


def _matches_trigger(path: str) -> bool:
    return any(p.search(path) for p in _TRIGGER_PATTERNS)


def find_affected_spec_ids(staged: list[str], tasks_dir: Path) -> set[str]:
    """Gibt alle Spec-IDs zurück deren Tasks test_files oder test_commands haben."""
    affected: set[str] = set()
    if not tasks_dir.exists():
        return affected
    for task_file in tasks_dir.glob("SPEC-*.json"):
        try:
            tasks = json.loads(task_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        spec_id = task_file.stem
        for task in tasks:
            if task.get("test_file") or task.get("test_ids"):
                affected.add(spec_id)
                break
    return affected


class PreCommitHook:
    def __init__(self, project_root: Path, cfg_raw: dict) -> None:
        self._root = Path(project_root)
        self._cfg = cfg_raw

    def run(self) -> int:
        compliance = self._cfg.get("compliance") or {}
        if not compliance.get("post_commit_hook", True):
            return 0

        staged = self._get_staged_files()
        triggered = [f for f in staged if _matches_trigger(f)]
        if not triggered:
            return 0

        tasks_dir = self._root / ".sdd" / "tasks"
        spec_ids = find_affected_spec_ids(triggered, tasks_dir)
        if not spec_ids:
            return 0

        return self._run_tests(spec_ids)

    def _get_staged_files(self) -> list[str]:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            cwd=self._root,
        )
        return [line for line in result.stdout.splitlines() if line.strip()]

    def _run_tests(self, spec_ids: set[str]) -> int:
        spec_filter = " or ".join(spec_ids)
        result = subprocess.run(
            ["pytest", "tests/", "-k", spec_filter, "--tb=short"],
            cwd=self._root,
        )
        return result.returncode


def apply_status_transitions(root: Path) -> list:
    """Führt die status-check-Logik intern aus (SPEC-0010 FR-02, CON-0167).

    Scheitert bewusst weich: ein Fehler hier meldet sich sichtbar, blockiert den
    Commit aber nicht. Ein Status-Check, der das Repository commit-unfähig macht,
    wäre schlimmer als ein übersprungener Status-Check.
    """
    import sys

    try:
        from .config import load_config
        from .lifecycle import apply_transitions, check_transitions

        cfg = load_config(root)
        changes = check_transitions(cfg)
        if changes:
            apply_transitions(cfg, changes)
            for c in changes:
                print(f"[sdd pre-commit] {c.artifact_id}: {c.old_status} → {c.new_status} "
                      f"(Inhalt geändert)")
            _restage(root, [c.path for c in changes])
        _seed_new_hashes(cfg)
        return changes
    except Exception as exc:
        print(f"[sdd pre-commit] Status-Check übersprungen: {exc}", file=sys.stderr)
        return []


def _seed_new_hashes(cfg) -> int:
    """Traegt Hashes fuer bisher unbekannte Artefakte nach (TST-0050 TC-03).

    check_transitions meldet nur Artefakte, fuer die bereits ein Hash gespeichert
    ist — ohne diesen Schritt bleibt `stored_hash` fuer jede neue Datei ewig None
    und es gibt nie einen Statuswechsel. Genau das war der Zustand: content-hashes.json
    wurde von keiner Produktivstelle je befuellt.

    Bestehende Hashes bleiben unangetastet, sonst ginge die Aenderungserkennung
    fuer bereits verfolgte Artefakte verloren.
    """
    from .lifecycle import load_hashes, rebuild_hashes, save_hashes

    hashes = load_hashes(cfg)
    added = 0
    for artifact_id, digest in rebuild_hashes(cfg).items():
        if artifact_id not in hashes:
            hashes[artifact_id] = digest
            added += 1
    if added:
        save_hashes(cfg, hashes)
    return added


def _restage(root: Path, paths: list[Path]) -> None:
    """Stagt gepatchte Dateien nach – aber nur die, die ohnehin im Commit sind.

    Andernfalls zöge der Hook fremde Arbeitskopie-Änderungen in den Commit.
    """
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True, text=True, cwd=root,
    )
    staged = {line.strip() for line in result.stdout.splitlines() if line.strip()}
    to_add = []
    for path in paths:
        try:
            rel = str(Path(path).resolve().relative_to(Path(root).resolve()))
        except ValueError:
            continue
        if rel in staged:
            to_add.append(rel)
    if to_add:
        subprocess.run(["git", "add", *to_add], cwd=root)


def main() -> int:
    """Entry-Point für das installierte Hook-Skript."""
    import sys

    cwd = Path.cwd()
    config_path = cwd / ".sdd" / "config.yaml"
    if not config_path.exists():
        return 0

    apply_status_transitions(cwd)

    import yaml
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    cfg_raw = raw if isinstance(raw, dict) else {}

    hook = PreCommitHook(project_root=cwd, cfg_raw=cfg_raw)
    code = hook.run()
    if code != 0:
        print(
            "\n[sdd pre-commit] Tests rot — Commit abgebrochen.\n"
            "  Nutze 'git commit --no-verify' um zu überspringen (wird protokolliert).",
            file=sys.stderr,
        )
    return code
