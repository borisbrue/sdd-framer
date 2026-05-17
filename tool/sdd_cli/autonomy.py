"""Autonomy Level Tracking für das Dark Factory Pattern.

Level-Kriterien (aus SPEC-0004 §3.5):

| Level | Bezeichnung       | Pass-Rate | Override-Rate | Min. PRs | Auto-Merge |
|-------|-------------------|-----------|---------------|----------|------------|
| 1     | Vollständig manuell| —         | —             | —        | nein       |
| 2     | AI-assisted       | —         | ≤ 100 %       | 0        | nein       |
| 3     | AI-reviewed       | ≥ 70 %    | ≤ 30 %        | 10       | nein       |
| 3.5   | AI-gated          | ≥ 85 %    | ≤ 15 %        | 20       | optional   |
| 4     | Fully autonomous  | ≥ 90 %    | ≤ 5 %         | 50       | ja         |

Rolling Window = Min. PRs des jeweiligen Levels.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .config import SddConfig


VALID_LEVELS = {1, 2, 3, 3.5, 4}

LEVEL_CRITERIA = {
    1:   {"label": "Vollständig manuell", "min_pass_rate": 0.0,  "max_override_rate": 1.0,  "min_prs": 0,  "auto_merge": False},
    2:   {"label": "AI-assisted",         "min_pass_rate": 0.0,  "max_override_rate": 1.0,  "min_prs": 0,  "auto_merge": False},
    3:   {"label": "AI-reviewed",         "min_pass_rate": 0.70, "max_override_rate": 0.30, "min_prs": 10, "auto_merge": False},
    3.5: {"label": "AI-gated",            "min_pass_rate": 0.85, "max_override_rate": 0.15, "min_prs": 20, "auto_merge": True},
    4:   {"label": "Fully autonomous",    "min_pass_rate": 0.90, "max_override_rate": 0.05, "min_prs": 50, "auto_merge": True},
}


@dataclass
class LevelStats:
    project_id: str
    current_level: float
    current_label: str
    total_prs: int
    pass_rate: float
    override_rate: float
    auto_merge_blocked: bool
    upgrade_proposal: Optional[float]
    downgrade_proposal: Optional[float]
    consecutive_below_threshold: int


def _db_path(config: SddConfig) -> Path:
    return config.sdd_dir / "evaluations.db"


def init_db(config: SddConfig) -> None:
    """Erstellt die evaluations.db-Tabellen falls nicht vorhanden."""
    db = _db_path(config)
    db.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS evaluations (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT    NOT NULL DEFAULT '',
                pr_number  TEXT    NOT NULL,
                hol_id     TEXT    NOT NULL,
                run_index  INTEGER NOT NULL,
                passed     INTEGER NOT NULL,
                timestamp  TEXT    NOT NULL,
                cost_usd   REAL    NOT NULL DEFAULT 0.0
            );
            CREATE TABLE IF NOT EXISTS pr_results (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT    NOT NULL DEFAULT '',
                pr_number  TEXT    NOT NULL UNIQUE,
                passed     INTEGER NOT NULL,
                pass_rate  REAL    NOT NULL,
                timestamp  TEXT    NOT NULL
            );
            CREATE TABLE IF NOT EXISTS false_positives (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT    NOT NULL DEFAULT '',
                pr_number  TEXT    NOT NULL,
                timestamp  TEXT    NOT NULL
            );
            CREATE TABLE IF NOT EXISTS resume_events (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                pr_number    TEXT    NOT NULL,
                triggered_by TEXT    NOT NULL DEFAULT 'cli',
                timestamp    TEXT    NOT NULL
            );
            CREATE TABLE IF NOT EXISTS token_usage (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp          TEXT    NOT NULL,
                spec_id            TEXT,
                component          TEXT    NOT NULL,
                model              TEXT    NOT NULL DEFAULT '',
                input_tokens       INTEGER NOT NULL DEFAULT 0,
                output_tokens      INTEGER NOT NULL DEFAULT 0,
                cache_read_tokens  INTEGER NOT NULL DEFAULT 0,
                cache_write_tokens INTEGER NOT NULL DEFAULT 0,
                duration_ms        INTEGER NOT NULL DEFAULT 0,
                calibrated         INTEGER NOT NULL DEFAULT 0
            );
        """)


def record_evaluation(
    config: SddConfig,
    project_id: str,
    pr_number: str,
    hol_id: str,
    run_index: int,
    passed: bool,
    cost_usd: float = 0.0,
) -> None:
    init_db(config)
    ts = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(_db_path(config)) as conn:
        conn.execute(
            "INSERT INTO evaluations (project_id, pr_number, hol_id, run_index, passed, timestamp, cost_usd)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (project_id, pr_number, hol_id, run_index, int(passed), ts, cost_usd),
        )


def record_pr_result(
    config: SddConfig,
    project_id: str,
    pr_number: str,
    passed: bool,
    pass_rate: float,
) -> None:
    init_db(config)
    ts = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(_db_path(config)) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO pr_results (project_id, pr_number, passed, pass_rate, timestamp)"
            " VALUES (?, ?, ?, ?, ?)",
            (project_id, pr_number, int(passed), pass_rate, ts),
        )


def record_false_positive(
    config: SddConfig,
    project_id: str,
    pr_number: str,
) -> None:
    init_db(config)
    ts = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(_db_path(config)) as conn:
        conn.execute(
            "INSERT INTO false_positives (project_id, pr_number, timestamp) VALUES (?, ?, ?)",
            (project_id, pr_number, ts),
        )


def record_resume_event(
    config: SddConfig,
    pr_number: str,
    triggered_by: str = "cli",
) -> None:
    init_db(config)
    ts = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(_db_path(config)) as conn:
        conn.execute(
            "INSERT INTO resume_events (pr_number, triggered_by, timestamp) VALUES (?, ?, ?)",
            (pr_number, triggered_by, ts),
        )


def _level_float(raw: object) -> float:
    """Normalisiert Levelangaben wie '3.5', 3, 3.5 auf float."""
    try:
        v = float(str(raw))
    except (TypeError, ValueError):
        return 1.0
    return v if v in VALID_LEVELS else 1.0


def compute_level_stats(
    config: SddConfig,
    project_id: str,
    current_level: float,
) -> LevelStats:
    """Berechnet aktuelle Metriken und Upgrade-/Downgrade-Vorschläge."""
    init_db(config)
    crit = LEVEL_CRITERIA.get(current_level, LEVEL_CRITERIA[1])
    window = crit["min_prs"] or 10

    with sqlite3.connect(_db_path(config)) as conn:
        rows = conn.execute(
            "SELECT passed, pass_rate FROM pr_results WHERE project_id = ?"
            " ORDER BY timestamp DESC LIMIT ?",
            (project_id, window),
        ).fetchall()
        total_prs = conn.execute(
            "SELECT COUNT(*) FROM pr_results WHERE project_id = ?",
            (project_id,),
        ).fetchone()[0]
        fp_count = conn.execute(
            "SELECT COUNT(*) FROM false_positives WHERE project_id = ?",
            (project_id,),
        ).fetchone()[0]

    if rows:
        pass_rate = sum(r[1] for r in rows) / len(rows)
    else:
        pass_rate = 0.0

    override_rate = (fp_count / total_prs) if total_prs else 0.0

    # Auto-Merge blockiert wenn Pass-Rate unter aktuellem Level-Minimum
    blocked = (
        current_level >= 3
        and total_prs >= crit["min_prs"]
        and pass_rate < crit["min_pass_rate"]
    )

    # Aufeinanderfolgende PRs unter Schwellwert (für Downgrade-Vorschlag)
    consecutive_below = 0
    for row in rows:
        if row[1] < crit["min_pass_rate"]:
            consecutive_below += 1
        else:
            break

    # Upgrade-Vorschlag prüfen
    upgrade_proposal = _check_upgrade(
        current_level, pass_rate, override_rate, total_prs, rows
    )

    # Downgrade-Vorschlag nach 5 aufeinanderfolgenden PRs unter Schwellwert
    downgrade_proposal = None
    if consecutive_below >= 5 and current_level > 1:
        levels = sorted(LEVEL_CRITERIA.keys())
        idx = levels.index(current_level)
        if idx > 0:
            downgrade_proposal = levels[idx - 1]

    label = LEVEL_CRITERIA.get(current_level, LEVEL_CRITERIA[1])["label"]
    return LevelStats(
        project_id=project_id,
        current_level=current_level,
        current_label=label,
        total_prs=total_prs,
        pass_rate=pass_rate,
        override_rate=override_rate,
        auto_merge_blocked=blocked,
        upgrade_proposal=upgrade_proposal,
        downgrade_proposal=downgrade_proposal,
        consecutive_below_threshold=consecutive_below,
    )


def _check_upgrade(
    current_level: float,
    pass_rate: float,
    override_rate: float,
    total_prs: int,
    recent_rows: list,
) -> Optional[float]:
    levels = sorted(LEVEL_CRITERIA.keys())
    if current_level not in levels:
        return None
    idx = levels.index(current_level)
    if idx >= len(levels) - 1:
        return None

    next_level = levels[idx + 1]
    next_crit = LEVEL_CRITERIA[next_level]
    window = next_crit["min_prs"]

    if window == 0:
        # Kein PR-Minimum – Rate-Kriterien direkt prüfen
        window_pass_rate = pass_rate
    else:
        if total_prs < window:
            return None
        if len(recent_rows) < window:
            return None
        window_pass_rate = sum(r[1] for r in recent_rows[:window]) / window
    if (
        window_pass_rate >= next_crit["min_pass_rate"]
        and override_rate <= next_crit["max_override_rate"]
    ):
        return next_level
    return None


def auto_merge_allowed(
    config: SddConfig,
    project_id: str,
    current_level: float,
    total_prs: int,
    pass_rate: float,
) -> tuple[bool, str]:
    """Gibt (allowed, reason) zurück.

    Prüft: Level-Minimum, Pass-Rate-Schwellwert, config.auto_merge.
    """
    crit = LEVEL_CRITERIA.get(current_level, LEVEL_CRITERIA[1])
    min_prs = crit["min_prs"]

    if not crit["auto_merge"]:
        return False, f"Auto-Merge nicht erlaubt für Level {current_level}."
    if total_prs < min_prs:
        return False, (
            f"Auto-Merge deaktiviert: {total_prs} PRs vorhanden, "
            f"Minimum für Level {current_level} ist {min_prs}."
        )
    if pass_rate < crit["min_pass_rate"]:
        return False, (
            f"Auto-Merge blockiert: Pass-Rate {pass_rate:.0%} "
            f"unter Schwellwert {crit['min_pass_rate']:.0%} für Level {current_level}."
        )
    return True, "Auto-Merge freigegeben."


def level_label(level: float) -> str:
    crit = LEVEL_CRITERIA.get(level)
    if not crit:
        return f"Level {level} (unbekannt)"
    return f"Level {level} — {crit['label']}"
