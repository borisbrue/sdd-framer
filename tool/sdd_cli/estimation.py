"""Token-Kostenschätzung via k=3 Nearest-Neighbor-Heuristik.

Implementiert SPEC-0011:
- Feature-Extraktion aus Spec-Dateien (ohne LLM)
- Persistenz in .sdd/evaluations.db (Tabelle token_usage)
- Kostenschätzung: Nearest Neighbor + konfigurierbare Preis-Tabelle
- CLI-Ausgabe: sdd estimate + sdd token-history
"""
from __future__ import annotations

import csv
import math
import re
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .config import SddConfig
from .frontmatter import parse_safe

TOKEN_USAGE_TABLE = "token_usage"

PRIORITY_WEIGHTS = {"critical": 4, "high": 3, "medium": 2, "low": 1}

_K = 3  # Nearest-Neighbor-Anzahl


# ─────────────────────────────────────────────────────────────────────────────
# DB-Initialisierung
# ─────────────────────────────────────────────────────────────────────────────

def _db_path(config: SddConfig) -> Path:
    return config.sdd_dir / "evaluations.db"


def init_token_usage_table(config: SddConfig) -> None:
    """Erstellt token_usage-Tabelle in evaluations.db, falls nicht vorhanden."""
    db = _db_path(config)
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
        # Migration: add task_id/task_label columns to existing tables (CON-0121)
        existing = {row[1] for row in conn.execute("PRAGMA table_info(token_usage)")}
        for col, typedef in (("task_id", "TEXT"), ("task_label", "TEXT")):
            if col not in existing:
                conn.execute(f"ALTER TABLE {TOKEN_USAGE_TABLE} ADD COLUMN {col} {typedef}")


# ─────────────────────────────────────────────────────────────────────────────
# Token-Persistenz (für alle LLM-Komponenten)
# ─────────────────────────────────────────────────────────────────────────────

def persist_token_usage(
    config: SddConfig,
    *,
    component: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
    duration_ms: int = 0,
    spec_id: str | None = None,
    task_id: str | None = None,
    task_label: str | None = None,
) -> None:
    """Schreibt tatsächlichen Token-Verbrauch einer LLM-Komponente in die DB."""
    try:
        init_token_usage_table(config)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        db = _db_path(config)
        with sqlite3.connect(db) as conn:
            conn.execute(
                f"""INSERT INTO {TOKEN_USAGE_TABLE}
                    (timestamp, spec_id, component, model,
                     input_tokens, output_tokens, cache_read_tokens,
                     cache_write_tokens, duration_ms, task_id, task_label)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (ts, spec_id, component, model,
                 input_tokens, output_tokens, cache_read_tokens,
                 cache_write_tokens, duration_ms, task_id, task_label),
            )
    except Exception:
        pass  # Persistenz-Fehler dürfen Hauptfluss nicht unterbrechen


# ─────────────────────────────────────────────────────────────────────────────
# Feature-Extraktion
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SpecFeatures:
    spec_id: str
    body_chars: int
    contract_count: int
    test_count: int
    user_story_count: int
    fr_count: int
    dependency_count: int
    priority_weight: int

    def as_vector(self) -> list[float]:
        return [
            float(self.body_chars),
            float(self.contract_count),
            float(self.test_count),
            float(self.user_story_count),
            float(self.fr_count),
            float(self.dependency_count),
            float(self.priority_weight),
        ]


def extract_features(spec_path: Path) -> SpecFeatures | None:
    doc = parse_safe(spec_path)
    if not doc or not doc.frontmatter:
        return None
    fm = doc.frontmatter
    body = doc.body or ""

    spec_id = fm.get("id", "")
    body_chars = len(body)
    contract_count = len(fm.get("contracts") or [])
    test_count = len(fm.get("tests") or [])
    user_story_count = len(re.findall(r"^\|\s*US-", body, re.MULTILINE))
    fr_count = len(re.findall(r"\*\*FR-", body))
    dependency_count = len(fm.get("depends_on") or [])
    priority_raw = str(fm.get("priority", "medium")).lower()
    priority_weight = PRIORITY_WEIGHTS.get(priority_raw, 2)

    return SpecFeatures(
        spec_id=spec_id,
        body_chars=body_chars,
        contract_count=contract_count,
        test_count=test_count,
        user_story_count=user_story_count,
        fr_count=fr_count,
        dependency_count=dependency_count,
        priority_weight=priority_weight,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Nearest-Neighbor-Schätzung
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class HistoricalPoint:
    spec_id: str | None
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int


def _load_historical(config: SddConfig) -> list[HistoricalPoint]:
    """Lädt alle kalibrierten oder alle Datenpunkte pro spec_id aus token_usage."""
    db = _db_path(config)
    if not db.exists():
        return []
    try:
        with sqlite3.connect(db) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(f"""
                SELECT spec_id,
                       SUM(input_tokens)       AS input_tokens,
                       SUM(output_tokens)      AS output_tokens,
                       SUM(cache_read_tokens)  AS cache_read_tokens,
                       SUM(cache_write_tokens) AS cache_write_tokens
                FROM {TOKEN_USAGE_TABLE}
                WHERE spec_id IS NOT NULL
                GROUP BY spec_id
            """).fetchall()
        return [
            HistoricalPoint(
                spec_id=r["spec_id"],
                input_tokens=r["input_tokens"] or 0,
                output_tokens=r["output_tokens"] or 0,
                cache_read_tokens=r["cache_read_tokens"] or 0,
                cache_write_tokens=r["cache_write_tokens"] or 0,
            )
            for r in rows
        ]
    except Exception:
        return []


def _normalize(vectors: list[list[float]]) -> tuple[list[list[float]], list[float], list[float]]:
    """Normalisiert Feature-Vektoren (Min-Max). Gibt normierte Vektoren + min/range zurück."""
    if not vectors:
        return [], [], []
    dim = len(vectors[0])
    mins = [min(v[i] for v in vectors) for i in range(dim)]
    maxs = [max(v[i] for v in vectors) for i in range(dim)]
    ranges = [mx - mn if mx != mn else 1.0 for mn, mx in zip(mins, maxs)]
    normed = [[(v[i] - mins[i]) / ranges[i] for i in range(dim)] for v in vectors]
    return normed, mins, ranges


def _euclidean(a: list[float], b: list[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


@dataclass
class Neighbor:
    spec_id: str | None
    input_tokens: int
    output_tokens: int
    distance: float
    similarity: float  # 0–1, 1=identisch


def _knn(
    target_vec: list[float],
    historical: list[HistoricalPoint],
    specs_dir: Path,
) -> tuple[list[Neighbor], int]:
    """k=3 nächste Nachbarn. Gibt Nachbarn + Gesamtanzahl Datenpunkte zurück."""
    feature_map: dict[str, SpecFeatures] = {}
    for md in specs_dir.rglob("*.md"):
        ft = extract_features(md)
        if ft and ft.spec_id:
            feature_map[ft.spec_id] = ft

    candidates: list[tuple[float, HistoricalPoint]] = []
    for hp in historical:
        if hp.spec_id not in feature_map:
            continue
        ft = feature_map[hp.spec_id]
        candidates.append((0.0, hp, ft.as_vector()))

    if not candidates:
        return [], 0

    all_vecs = [target_vec] + [c[2] for c in candidates]
    normed, mins, ranges = _normalize(all_vecs)
    normed_target = normed[0]
    normed_candidates = normed[1:]

    scored: list[tuple[float, HistoricalPoint]] = []
    for i, (_, hp, _) in enumerate(candidates):
        dist = _euclidean(normed_target, normed_candidates[i])
        scored.append((dist, hp))

    scored.sort(key=lambda x: x[0])
    top_k = scored[:_K]

    max_dist = max((d for d, _ in scored), default=1.0) or 1.0
    neighbors = [
        Neighbor(
            spec_id=hp.spec_id,
            input_tokens=hp.input_tokens,
            output_tokens=hp.output_tokens,
            distance=dist,
            similarity=round(1.0 - dist / max_dist, 3),
        )
        for dist, hp in top_k
    ]
    return neighbors, len(historical)


# ─────────────────────────────────────────────────────────────────────────────
# Kostenkalkulation
# ─────────────────────────────────────────────────────────────────────────────

def _cost_config(config: SddConfig) -> dict:
    return config.raw.get("cost_estimation", {})


def _model_price(config: SddConfig, model: str) -> dict:
    prices = _cost_config(config).get("model_prices", {})
    return prices.get(model) or prices.get("default") or {
        "input_per_million": 3.00,
        "output_per_million": 15.00,
        "cache_write_per_million": 1.00,
        "cache_read_per_million": 0.08,
    }


def _calc_usd(price: dict, input_t: int, output_t: int,
              cache_read_t: int = 0, cache_write_t: int = 0) -> float:
    usd = (
        input_t * price.get("input_per_million", 3.00) / 1_000_000
        + output_t * price.get("output_per_million", 15.00) / 1_000_000
        + cache_read_t * price.get("cache_read_per_million", 0.08) / 1_000_000
        + cache_write_t * price.get("cache_write_per_million", 1.00) / 1_000_000
    )
    return round(usd, 6)


def _confidence(n_points: int) -> str:
    if n_points < 3:
        return "LOW"
    if n_points < 10:
        return "MEDIUM"
    return "HIGH"


# ─────────────────────────────────────────────────────────────────────────────
# Öffentliche Schätzfunktion
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class EstimateResult:
    spec_id: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    estimated_usd: float
    confidence: str  # LOW | MEDIUM | HIGH
    model: str
    model_fallback: bool
    neighbors: list[Neighbor] = field(default_factory=list)
    n_data_points: int = 0
    budget_exceeded: bool = False
    budget_limit_usd: float = 0.0

    def to_dict(self) -> dict:
        return {
            "spec_id": self.spec_id,
            "estimated_input_tokens": self.input_tokens,
            "estimated_output_tokens": self.output_tokens,
            "estimated_cache_read_tokens": self.cache_read_tokens,
            "estimated_cache_write_tokens": self.cache_write_tokens,
            "estimated_usd": self.estimated_usd,
            "confidence": self.confidence,
            "model": self.model,
            "model_fallback": self.model_fallback,
            "n_data_points": self.n_data_points,
            "budget_exceeded": self.budget_exceeded,
            "budget_limit_usd": self.budget_limit_usd,
            "neighbors": [
                {
                    "spec_id": n.spec_id,
                    "input_tokens": n.input_tokens,
                    "output_tokens": n.output_tokens,
                    "similarity": n.similarity,
                }
                for n in self.neighbors
            ],
        }


def estimate(
    config: SddConfig,
    spec_id: str,
    model_override: str | None = None,
) -> EstimateResult:
    """Schätzt Token-Verbrauch für eine Spec via k=3 Nearest Neighbor."""
    # Feature-Extraktion
    spec_path = _find_spec(config, spec_id)
    if spec_path is None:
        raise ValueError(f"Spec nicht gefunden: {spec_id}")

    features = extract_features(spec_path)
    if features is None:
        raise ValueError(f"Feature-Extraktion fehlgeschlagen: {spec_id}")

    cost_cfg = _cost_config(config)
    model = model_override or cost_cfg.get("default_model", "claude-haiku-4-5-20251001")
    prices = _model_price(config, model)
    model_fallback = (model_override is None and
                      model not in cost_cfg.get("model_prices", {}))

    historical = _load_historical(config)
    neighbors, n_points = _knn(features.as_vector(), historical, config.specs_dir)

    if neighbors:
        # Gewichteter Durchschnitt (1/distance; identisch → weight=1.0)
        weights = [1.0 / (n.distance + 1e-9) for n in neighbors]
        total_w = sum(weights)
        est_input = int(sum(w * n.input_tokens for w, n in zip(weights, neighbors)) / total_w)
        est_output = int(sum(w * n.output_tokens for w, n in zip(weights, neighbors)) / total_w)
        est_cache_r = int(sum(w * n.input_tokens * 0.1 for w, n in zip(weights, neighbors)) / total_w)
        est_cache_w = 0
    else:
        # Fallback: grobe Heuristik auf Basis body_chars
        est_input = max(500, features.body_chars // 4)
        est_output = max(200, est_input // 5)
        est_cache_r = 0
        est_cache_w = 0

    usd = _calc_usd(prices, est_input, est_output, est_cache_r, est_cache_w)
    confidence = _confidence(n_points)
    budget_limit = cost_cfg.get("budget_alert_usd", 0.0)
    budget_exceeded = bool(budget_limit and usd > budget_limit)

    return EstimateResult(
        spec_id=spec_id,
        input_tokens=est_input,
        output_tokens=est_output,
        cache_read_tokens=est_cache_r,
        cache_write_tokens=est_cache_w,
        estimated_usd=usd,
        confidence=confidence,
        model=model,
        model_fallback=model_fallback,
        neighbors=neighbors,
        n_data_points=n_points,
        budget_exceeded=budget_exceeded,
        budget_limit_usd=budget_limit,
    )


def _find_spec(config: SddConfig, spec_id: str) -> Path | None:
    if not config.specs_dir.exists():
        return None
    for md in config.specs_dir.rglob("*.md"):
        doc = parse_safe(md)
        if doc and doc.frontmatter.get("id") == spec_id:
            return md
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Token-History
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class TokenHistoryRow:
    id: int
    timestamp: str
    spec_id: str | None
    component: str
    model: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    duration_ms: int
    task_id: str | None = None
    task_label: str | None = None


def token_history(
    config: SddConfig,
    spec_id: str | None = None,
) -> list[TokenHistoryRow]:
    """Lädt Token-History aus der DB, optional gefiltert nach spec_id."""
    db = _db_path(config)
    if not db.exists():
        return []
    try:
        with sqlite3.connect(db) as conn:
            conn.row_factory = sqlite3.Row
            if spec_id:
                rows = conn.execute(
                    f"SELECT * FROM {TOKEN_USAGE_TABLE} WHERE spec_id = ? ORDER BY id",
                    (spec_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    f"SELECT * FROM {TOKEN_USAGE_TABLE} ORDER BY id"
                ).fetchall()
        return [
            TokenHistoryRow(
                id=r["id"],
                timestamp=r["timestamp"],
                spec_id=r["spec_id"],
                component=r["component"],
                model=r["model"],
                input_tokens=r["input_tokens"],
                output_tokens=r["output_tokens"],
                cache_read_tokens=r["cache_read_tokens"],
                cache_write_tokens=r["cache_write_tokens"],
                duration_ms=r["duration_ms"],
                task_id=r["task_id"] if "task_id" in r.keys() else None,
                task_label=r["task_label"] if "task_label" in r.keys() else None,
            )
            for r in rows
        ]
    except Exception:
        return []


def export_token_history_csv(config: SddConfig, csv_path: Path) -> int:
    """Exportiert alle Token-Datenpunkte als CSV. Gibt Zeilenanzahl zurück."""
    rows = token_history(config)
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow([
            "id", "timestamp", "spec_id", "component", "model",
            "input_tokens", "output_tokens", "cache_read_tokens",
            "cache_write_tokens", "duration_ms",
        ])
        for r in rows:
            writer.writerow([
                r.id, r.timestamp, r.spec_id or "", r.component, r.model,
                r.input_tokens, r.output_tokens, r.cache_read_tokens,
                r.cache_write_tokens, r.duration_ms,
            ])
    return len(rows)


# ─────────────────────────────────────────────────────────────────────────────
# Kalibrierung
# ─────────────────────────────────────────────────────────────────────────────

def calibrate(config: SddConfig, spec_id: str) -> dict:
    """Summiert Token-Verbrauch einer Spec und markiert Einträge als calibrated=1."""
    db = _db_path(config)
    if not db.exists():
        raise FileNotFoundError("evaluations.db nicht gefunden.")
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(f"""
            SELECT SUM(input_tokens)       AS input_tokens,
                   SUM(output_tokens)      AS output_tokens,
                   SUM(cache_read_tokens)  AS cache_read_tokens,
                   SUM(cache_write_tokens) AS cache_write_tokens,
                   COUNT(*)               AS n
            FROM {TOKEN_USAGE_TABLE}
            WHERE spec_id = ?
        """, (spec_id,)).fetchone()
        conn.execute(
            f"UPDATE {TOKEN_USAGE_TABLE} SET calibrated = 1 WHERE spec_id = ?",
            (spec_id,),
        )
        task_rows = conn.execute(f"""
            SELECT task_id, task_label,
                   SUM(input_tokens)      AS input_tokens,
                   SUM(output_tokens)     AS output_tokens,
                   SUM(cache_read_tokens) AS cache_read_tokens,
                   COUNT(*)              AS n
            FROM {TOKEN_USAGE_TABLE}
            WHERE spec_id = ? AND task_id IS NOT NULL
            GROUP BY task_id, task_label
            ORDER BY MIN(id)
        """, (spec_id,)).fetchall()
    tasks = [
        {
            "task_id": tr["task_id"],
            "task_label": tr["task_label"],
            "input_tokens": tr["input_tokens"] or 0,
            "output_tokens": tr["output_tokens"] or 0,
            "cache_read_tokens": tr["cache_read_tokens"] or 0,
            "n_entries": tr["n"] or 0,
        }
        for tr in task_rows
    ]
    return {
        "spec_id": spec_id,
        "input_tokens": row["input_tokens"] or 0,
        "output_tokens": row["output_tokens"] or 0,
        "cache_read_tokens": row["cache_read_tokens"] or 0,
        "cache_write_tokens": row["cache_write_tokens"] or 0,
        "n_entries": row["n"] or 0,
        "tasks": tasks,
    }
