"""Tabelle `token_usage` in `.sdd/evaluations.db` (SPEC-0011, SPEC-0060 FR-05).

Die Definition liegt in der LLM-Schicht, weil die Usage-Senke (`usage.SqliteUsageSink`) sie
braucht und die LLM-Schicht nur von `core` abhängen darf (SPEC-0058 FR-08, ARCH-02).
`estimation.py` liest und re-exportiert sie.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

TOKEN_USAGE_TABLE = "token_usage"

# Additive Migrationen: CON-0121 (task_*), CON-0129 (agent_type), SPEC-0060 FR-05 (Rest).
_MIGRATION_COLUMNS = (
    ("task_id", "TEXT"),
    ("task_label", "TEXT"),
    ("agent_type", "TEXT"),  # CON-0129: "local" | "cloud" | NULL
    ("reasoning_tokens", "INTEGER"),
    ("finish_reason", "TEXT"),
    ("server_model", "TEXT"),
    ("source", "TEXT"),  # CON-0206 INV-02: reported | estimated | unavailable | NULL (Altzeile)
    ("run_id", "TEXT"),
    ("context_json", "TEXT"),
)



def init_token_usage_table_at(sdd_dir: Path) -> Path:
    """Legt token_usage in `sdd_dir/evaluations.db` an bzw. migriert sie; gibt den DB-Pfad zurück."""
    db = sdd_dir / "evaluations.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db) as conn:
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {TOKEN_USAGE_TABLE} (
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
                calibrated         INTEGER NOT NULL DEFAULT 0,
                task_id            TEXT,
                task_label         TEXT
            )
        """)
        existing = {row[1] for row in conn.execute("PRAGMA table_info(token_usage)")}
        for col, typedef in _MIGRATION_COLUMNS:
            if col not in existing:
                conn.execute(f"ALTER TABLE {TOKEN_USAGE_TABLE} ADD COLUMN {col} {typedef}")
    return db
