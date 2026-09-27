"""`sdd bench run`: Matrix ausführen, Resume, Stufenmodell (SPEC-0056 FR-01, FR-05, FR-09).

`results.jsonl` ist Protokoll und Fortschritt zugleich (Memento): `--resume` führt nur Läufe aus,
für die kein Record mit Ausgang `completed` oder `halted: budget` existiert; ein `error`-Record wird
ersetzt (CON-0223 INV-06).
"""
from __future__ import annotations

import json
import statistics
import threading
from collections import defaultdict
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from ..config import SddConfig
from ..pipeline.schemas import errors as schema_errors
from .config import Matrix, load_suite
from .suites import Job, jobs_for, task_class

RESULTS = Path("bench") / "results"
FINAL = ("completed", "halted: budget")


def results_dir(root: Path) -> Path:
    stempel = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    return root / RESULTS / stempel


def read_records(ordner: Path) -> list[dict]:
    pfad = ordner / "results.jsonl"
    if not pfad.is_file():
        return []
    return [json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]


def write_records(ordner: Path, records: list[dict]) -> None:
    ordner.mkdir(parents=True, exist_ok=True)
    (ordner / "results.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")


@dataclass
class Plan:
    jobs: list[Job]
    filtered: dict[str, list[str]] = field(default_factory=dict)


def top_profiles(records: list[dict], top_k: int) -> dict[str, set[str]]:
    """Je Rolle die `top_k` besten Profile nach mittlerem Q der Suite roles (FR-05)."""
    werte: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for r in records:
        if r.get("q_kind") == "eval" and r.get("Q") is not None:
            werte[r["role"]][r["profile"]].append(r["Q"])
    return {rolle: {p for p, _ in sorted(profile.items(), key=lambda kv: -statistics.fmean(
        kv[1]))[:top_k]} for rolle, profile in werte.items()}


def run_matrix(config: SddConfig, matrix: Matrix, *, suite: str | None = None,
               only: str | None = None, repetitions: int | None = None, concurrency: int = 1,
               resume: Path | None = None, dry_run: bool = False,
               notify: Callable[[str], None] = lambda _m: None) -> tuple[Path | None, Plan]:
    ordner = resume or results_dir(config.root)
    bisher = read_records(ordner) if resume else []
    fertig = {r["run_id"] for r in bisher if r.get("outcome") in FINAL}
    records = [r for r in bisher if r["run_id"] in fertig]
    plan = Plan([])
    sperre = threading.Lock()
    suiten = [suite] if suite else matrix.suites
    for name in suiten:
        s = load_suite(config.root, name)
        task_class(s.kind)  # unbekannte Art: BenchError vor jedem Aufruf
        erlaubt = (top_profiles(records, matrix.top_k)
                   if matrix.top_k and s.kind != "roles" else None)
        jobs, gefiltert = jobs_for(s, matrix, only=only, repetitions=repetitions,
                                   allowed=erlaubt)
        if gefiltert:
            plan.filtered[name] = gefiltert
        offen = [j for j in jobs if j.run_id not in fertig]
        plan.jobs.extend(offen)
        if dry_run:
            continue
        notify(f"▶ Suite {name} ({s.kind}): {len(offen)} Läufe")

        def ausfuehren(job: Job) -> dict:
            task = task_class(job.suite.kind)(config, matrix, job, ordner / "runs" / job.run_id)
            record = task.execute()
            fehler = schema_errors("bench-record", record)
            if fehler:
                record = {**record, "outcome": "error",
                          "error": f"Record verletzt CON-0222: {fehler[0]}"}
            with sperre:
                records.append(record)
                write_records(ordner, records)
            notify(f"  {job.run_id}: {record['outcome']}, Q={record.get('Q')}")
            return record

        with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
            list(pool.map(ausfuehren, offen))
    if dry_run:
        return None, plan
    if plan.filtered:
        (ordner / "filtered.json").write_text(json.dumps(plan.filtered, indent=2) + "\n",
                                              encoding="utf-8")
    write_records(ordner, records)
    return ordner, plan
