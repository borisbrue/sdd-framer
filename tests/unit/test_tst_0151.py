# TST-0151 – Token-History agent_type/model Erweiterung (CON-0129)
# Spec: SPEC-0036 | Level: contract | Contract: CON-0129

import sqlite3
import tempfile
from pathlib import Path

import pytest

from sdd_cli.config import SddConfig
from sdd_cli.estimation import (
    TokenHistoryRow,
    init_token_usage_table,
    persist_token_usage,
    token_history,
)


@pytest.fixture
def tmp_config(tmp_path: Path) -> SddConfig:
    sdd_dir = tmp_path / ".sdd"
    sdd_dir.mkdir()
    return SddConfig(root=tmp_path, raw={})


class TestTST0151:
    def test_persist_and_read_agent_type_local(self, tmp_config: SddConfig) -> None:
        # INV-04: lokaler Task → agent_type="local", model=lokales Modell
        persist_token_usage(
            tmp_config,
            component="sdd-implement-subagent",
            model="llama3.1:8b",
            input_tokens=100,
            output_tokens=50,
            spec_id="SPEC-0036",
            task_id="t-001",
            task_label="Implement RoutingStrategy",
            agent_type="local",
        )
        rows = token_history(tmp_config, spec_id="SPEC-0036")
        assert len(rows) == 1
        assert rows[0].agent_type == "local"
        assert rows[0].model == "llama3.1:8b"

    def test_persist_and_read_agent_type_cloud(self, tmp_config: SddConfig) -> None:
        # INV-04: Cloud-Task → agent_type="cloud", model=cloud model-ID
        persist_token_usage(
            tmp_config,
            component="sdd-implement-subagent",
            model="claude-sonnet-4-6",
            input_tokens=500,
            output_tokens=200,
            spec_id="SPEC-0036",
            task_id="t-002",
            task_label="Implement AuthMiddleware",
            agent_type="cloud",
        )
        rows = token_history(tmp_config, spec_id="SPEC-0036")
        assert any(r.agent_type == "cloud" and r.model == "claude-sonnet-4-6" for r in rows)

    def test_backward_compat_no_agent_type(self, tmp_config: SddConfig) -> None:
        # INV-03: Einträge ohne agent_type bleiben gültig (Rückwärtskompatibilität)
        persist_token_usage(
            tmp_config,
            component="sdd-analyze",
            model="claude-sonnet-4-6",
            input_tokens=300,
            output_tokens=100,
            spec_id="SPEC-0036",
        )
        rows = token_history(tmp_config, spec_id="SPEC-0036")
        assert any(r.agent_type is None for r in rows)

    def test_agent_type_null_in_existing_table(self, tmp_config: SddConfig) -> None:
        # INV-03: Tabelle mit altem Schema (kein agent_type) kann migriert werden
        db_path = tmp_config.sdd_dir / "evaluations.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        # Altes Schema ohne agent_type anlegen
        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                CREATE TABLE token_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    spec_id TEXT,
                    component TEXT NOT NULL,
                    model TEXT NOT NULL DEFAULT '',
                    input_tokens INTEGER NOT NULL DEFAULT 0,
                    output_tokens INTEGER NOT NULL DEFAULT 0,
                    cache_read_tokens INTEGER NOT NULL DEFAULT 0,
                    cache_write_tokens INTEGER NOT NULL DEFAULT 0,
                    duration_ms INTEGER NOT NULL DEFAULT 0,
                    calibrated INTEGER NOT NULL DEFAULT 0,
                    task_id TEXT,
                    task_label TEXT
                )
            """)
            conn.execute("""
                INSERT INTO token_usage (timestamp, spec_id, component, model, input_tokens, output_tokens)
                VALUES ('2026-01-01T00:00:00Z', 'SPEC-OLD', 'sdd-analyze', 'claude-sonnet', 100, 50)
            """)
        # Migration ausführen
        init_token_usage_table(tmp_config)
        # Alten Eintrag lesen → agent_type ist NULL
        rows = token_history(tmp_config, spec_id="SPEC-OLD")
        assert len(rows) == 1
        assert rows[0].agent_type is None

    def test_agent_type_only_local_or_cloud_or_null(self, tmp_config: SddConfig) -> None:
        # INV-01: nur "local", "cloud" oder None erlaubt
        for at in ("local", "cloud", None):
            persist_token_usage(
                tmp_config,
                component="test",
                model="m",
                input_tokens=1,
                output_tokens=1,
                agent_type=at,
            )
        rows = token_history(tmp_config)
        for r in rows:
            assert r.agent_type in ("local", "cloud", None)
