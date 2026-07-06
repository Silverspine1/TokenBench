"""Ingest run artifacts into a queryable SQLite database.

Walks a ``runs/`` tree and folds each run's JSON artifacts — ``score.json``,
``telemetry.json``, ``manual_ide.json``, ``manual_cost.json``,
``staged_score.json`` — into flat tables keyed by ``run_id``. Idempotent:
re-ingesting the same runs replaces their rows (``INSERT OR REPLACE``), so it is
safe to re-run after new results land. Pure read of the artifacts; nothing here
recomputes a score.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    condition_id TEXT,
    trial_index INTEGER,
    repo_id TEXT,
    task_id TEXT,
    mode TEXT,
    category TEXT,
    difficulty TEXT,
    runner TEXT,
    success INTEGER,
    quality_score REAL,
    efficiency_score REAL,
    efficiency_gated REAL,
    final_score REAL,
    hidden_tests_total INTEGER,
    hidden_tests_passed INTEGER,
    hidden_pass_rate REAL,
    visible_tests_total INTEGER,
    visible_tests_passed INTEGER,
    visible_pass_rate REAL,
    forbidden_modified INTEGER,
    timed_out INTEGER,
    dependency_download_events INTEGER,
    total_wall_time_seconds REAL,
    run_dir TEXT
);

CREATE TABLE IF NOT EXISTS telemetry (
    run_id TEXT PRIMARY KEY,
    prompt_tokens INTEGER,
    agent_output_tokens INTEGER,
    tool_test_tokens INTEGER,
    patch_tokens INTEGER,
    total_observed_tokens INTEGER,
    total_log_bytes INTEGER,
    patch_bytes INTEGER,
    line_churn INTEGER,
    changed_files_total INTEGER,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE TABLE IF NOT EXISTS provider_cost (
    run_id TEXT PRIMARY KEY,
    available INTEGER,
    source TEXT,
    cost_usd REAL,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cache_read_tokens INTEGER,
    cache_write_tokens INTEGER,
    reasoning_tokens INTEGER,
    total_tokens INTEGER,
    manual_source TEXT,
    confidence TEXT,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE TABLE IF NOT EXISTS manual_runs (
    run_id TEXT PRIMARY KEY,
    mode TEXT,
    ide_name TEXT,
    ide_version TEXT,
    model_name TEXT,
    condition_id TEXT,
    candidate_source TEXT,
    started_at TEXT,
    submitted_at TEXT,
    stage INTEGER,
    stage_group_id TEXT,
    previous_run_id TEXT,
    status TEXT,
    run_dir TEXT
);

CREATE TABLE IF NOT EXISTS staged_scores (
    run_id TEXT PRIMARY KEY,
    stage_group_id TEXT,
    condition_id TEXT,
    stage1_run_id TEXT,
    stage1_quality REAL,
    stage2_quality REAL,
    extension_friction REAL,
    extension_friction_score REAL,
    staged_score REAL,
    run_dir TEXT
);

-- One row per run with the figures you most often want together.
CREATE VIEW IF NOT EXISTS run_results AS
SELECT
    r.run_id, r.condition_id, r.repo_id, r.task_id, r.category, r.difficulty,
    r.success, r.quality_score, r.final_score,
    r.hidden_tests_passed, r.hidden_tests_total,
    c.cost_usd, c.source AS cost_source,
    t.total_observed_tokens, t.line_churn,
    r.total_wall_time_seconds, r.run_dir
FROM runs r
LEFT JOIN provider_cost c ON c.run_id = r.run_id
LEFT JOIN telemetry t ON t.run_id = r.run_id;
"""


# Tables an admin UI may read/edit/delete. The read-only ``run_results`` view is
# intentionally excluded from writes. Used as an allowlist so a table name from
# an HTTP request can never be interpolated into SQL unchecked.
EDITABLE_TABLES = (
    "runs",
    "telemetry",
    "provider_cost",
    "manual_runs",
    "staged_scores",
)
PRIMARY_KEY = "run_id"


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _require_table(table: str) -> str:
    if table not in EDITABLE_TABLES:
        raise ValueError(f"unknown or non-editable table: {table!r}")
    return table


def table_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    _require_table(table)
    return [r["name"] for r in conn.execute(f"PRAGMA table_info({table})")]


def list_tables(db_path: Path) -> list[dict]:
    """Editable tables with their row counts (missing DB => zeros)."""
    db_path = Path(db_path)
    if not db_path.exists():
        return [{"name": t, "count": 0} for t in EDITABLE_TABLES]
    conn = connect(db_path)
    try:
        out = []
        existing = {
            r["name"]
            for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        for t in EDITABLE_TABLES:
            n = conn.execute(f"SELECT COUNT(*) AS n FROM {t}").fetchone()["n"] if t in existing else 0
            out.append({"name": t, "count": n})
        return out
    finally:
        conn.close()


def fetch_rows(db_path: Path, table: str, limit: int = 500, offset: int = 0) -> dict:
    """Return ``{columns, rows}`` for one table (rows newest run_id first)."""
    _require_table(table)
    conn = connect(Path(db_path))
    try:
        cols = table_columns(conn, table)
        order = PRIMARY_KEY if PRIMARY_KEY in cols else cols[0]
        rows = [
            dict(r)
            for r in conn.execute(
                f"SELECT * FROM {table} ORDER BY {order} DESC LIMIT ? OFFSET ?",
                (int(limit), int(offset)),
            )
        ]
        return {"table": table, "columns": cols, "rows": rows}
    finally:
        conn.close()


def update_row(db_path: Path, table: str, pk_value: str, updates: dict) -> int:
    """Update one row by primary key. Only real columns (except the PK) are set.

    Returns the number of rows changed. Raises ValueError on a bad table or when
    no valid column is supplied.
    """
    _require_table(table)
    conn = connect(Path(db_path))
    try:
        cols = set(table_columns(conn, table))
        sets = {k: v for k, v in updates.items() if k in cols and k != PRIMARY_KEY}
        if not sets:
            raise ValueError("no valid columns to update")
        assignments = ", ".join(f"{k} = ?" for k in sets)
        params = list(sets.values()) + [pk_value]
        cur = conn.execute(
            f"UPDATE {table} SET {assignments} WHERE {PRIMARY_KEY} = ?", params
        )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def delete_row(db_path: Path, table: str, pk_value: str) -> int:
    """Delete one DB row by primary key. Does NOT touch run files on disk."""
    _require_table(table)
    conn = connect(Path(db_path))
    try:
        cur = conn.execute(f"DELETE FROM {table} WHERE {PRIMARY_KEY} = ?", (pk_value,))
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def _load(run_dir: Path, name: str) -> Optional[dict]:
    p = run_dir / name
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _upsert(conn: sqlite3.Connection, table: str, row: dict) -> None:
    cols = list(row)
    placeholders = ", ".join("?" for _ in cols)
    col_list = ", ".join(cols)
    conn.execute(
        f"INSERT OR REPLACE INTO {table} ({col_list}) VALUES ({placeholders})",
        [row[c] for c in cols],
    )


def ingest_run(conn: sqlite3.Connection, run_dir: Path) -> dict:
    """Fold one run directory's artifacts into the DB. Returns what was found."""
    run_dir = Path(run_dir)
    run_id = run_dir.name
    found = {"score": False, "telemetry": False, "cost": False,
             "manual": False, "staged": False}

    score = _load(run_dir, "score.json")
    if score:
        found["score"] = True
        ht = score.get("hidden_tests", {})
        vt = score.get("visible_tests", {})
        pen = score.get("penalties", {})
        timing = score.get("timing", {})
        _upsert(conn, "runs", {
            "run_id": score.get("run_id", run_id),
            "condition_id": score.get("condition_id"),
            "trial_index": score.get("trial_index"),
            "repo_id": score.get("repo_id"),
            "task_id": score.get("task_id"),
            "mode": score.get("mode"),
            "category": score.get("category"),
            "difficulty": score.get("difficulty"),
            "runner": score.get("runner"),
            "success": int(bool(score.get("success"))),
            "quality_score": score.get("quality_score"),
            "efficiency_score": score.get("efficiency_score"),
            "efficiency_gated": score.get("efficiency_gated"),
            "final_score": score.get("final_score"),
            "hidden_tests_total": ht.get("tests_total"),
            "hidden_tests_passed": ht.get("tests_passed"),
            "hidden_pass_rate": ht.get("pass_rate"),
            "visible_tests_total": vt.get("tests_total"),
            "visible_tests_passed": vt.get("tests_passed"),
            "visible_pass_rate": vt.get("pass_rate"),
            "forbidden_modified": int(bool(pen.get("forbidden_path_modified"))),
            "timed_out": int(bool(pen.get("timed_out"))),
            "dependency_download_events": pen.get("dependency_download_events"),
            "total_wall_time_seconds": timing.get("total_wall_time_seconds"),
            "run_dir": run_dir.as_posix(),
        })

    telemetry = _load(run_dir, "telemetry.json")
    if telemetry:
        found["telemetry"] = True
        tok = telemetry.get("token_estimates", {})
        patch = telemetry.get("patch", {})
        logs = telemetry.get("logs", {})
        _upsert(conn, "telemetry", {
            "run_id": run_id,
            "prompt_tokens": tok.get("prompt_input_tokens"),
            "agent_output_tokens": tok.get("agent_total_output_tokens"),
            "tool_test_tokens": tok.get("tool_test_output_tokens"),
            "patch_tokens": tok.get("patch_tokens"),
            "total_observed_tokens": tok.get("total_observed_tokens"),
            "total_log_bytes": logs.get("total_log_bytes"),
            "patch_bytes": patch.get("patch_bytes"),
            "line_churn": patch.get("line_churn"),
            "changed_files_total": patch.get("changed_files_total"),
        })

        pu = telemetry.get("provider_usage") or {}
        manual_cost = _load(run_dir, "manual_cost.json") or {}
        if pu or manual_cost:
            found["cost"] = bool(pu.get("available")) or bool(manual_cost)
            _upsert(conn, "provider_cost", {
                "run_id": run_id,
                "available": int(bool(pu.get("available"))),
                "source": pu.get("source"),
                "cost_usd": pu.get("cost_usd"),
                "input_tokens": pu.get("input_tokens"),
                "output_tokens": pu.get("output_tokens"),
                "cache_read_tokens": pu.get("cache_read_tokens"),
                "cache_write_tokens": pu.get("cache_write_tokens"),
                "reasoning_tokens": pu.get("reasoning_tokens"),
                "total_tokens": pu.get("total_tokens"),
                "manual_source": manual_cost.get("source"),
                "confidence": manual_cost.get("confidence"),
            })

    manual = _load(run_dir, "manual_ide.json")
    if manual:
        found["manual"] = True
        from ..manual.service import run_status

        _upsert(conn, "manual_runs", {
            "run_id": manual.get("run_id", run_id),
            "mode": manual.get("mode"),
            "ide_name": manual.get("ide_name"),
            "ide_version": manual.get("ide_version"),
            "model_name": manual.get("model_name"),
            "condition_id": manual.get("condition_id"),
            "candidate_source": manual.get("candidate_source"),
            "started_at": manual.get("started_at"),
            "submitted_at": manual.get("submitted_at"),
            "stage": manual.get("stage"),
            "stage_group_id": manual.get("stage_group_id"),
            "previous_run_id": manual.get("previous_run_id"),
            "status": run_status(run_dir),
            "run_dir": run_dir.as_posix(),
        })

    staged = _load(run_dir, "staged_score.json")
    if staged:
        found["staged"] = True
        s = staged.get("staged", {})
        _upsert(conn, "staged_scores", {
            "run_id": run_id,
            "stage_group_id": staged.get("stage_group_id"),
            "condition_id": staged.get("condition_id"),
            "stage1_run_id": staged.get("stage1", {}).get("run_id"),
            "stage1_quality": s.get("stage1_quality"),
            "stage2_quality": s.get("stage2_quality"),
            "extension_friction": s.get("extension_friction"),
            "extension_friction_score": s.get("extension_friction_score"),
            "staged_score": s.get("staged_score"),
            "run_dir": run_dir.as_posix(),
        })

    return found


def _is_run_dir(p: Path) -> bool:
    """A run dir is any directory carrying at least one known artifact."""
    return p.is_dir() and any(
        (p / name).exists()
        for name in ("score.json", "manual_ide.json", "telemetry.json")
    )


def ingest_runs(runs_root: Path, db_path: Path) -> dict:
    """Ingest every run directory under ``runs_root`` into ``db_path``.

    Returns counts of rows touched per table.
    """
    runs_root = Path(runs_root)
    conn = connect(Path(db_path))
    try:
        create_schema(conn)
        totals = {"runs": 0, "telemetry": 0, "cost": 0, "manual": 0, "staged": 0}
        dirs = sorted(p for p in runs_root.iterdir() if _is_run_dir(p)) if runs_root.exists() else []
        for run_dir in dirs:
            found = ingest_run(conn, run_dir)
            totals["runs"] += int(found["score"])
            totals["telemetry"] += int(found["telemetry"])
            totals["cost"] += int(found["cost"])
            totals["manual"] += int(found["manual"])
            totals["staged"] += int(found["staged"])
        conn.commit()
        totals["run_dirs_scanned"] = len(dirs)
        totals["db_path"] = Path(db_path).as_posix()
        return totals
    finally:
        conn.close()
