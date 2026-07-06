"""Build chart-ready series from the results SQLite database.

Turns the flat ingested tables into per-condition series for the UI chart
builder. The headline use case: cumulative provider tokens (or cost, score,
effort) for one condition vs another, with tests ordered along the X-axis by run
time. All aggregation/ordering/cumulation happens here so the front-end only
draws what it is given.
"""

from __future__ import annotations

import statistics
from pathlib import Path

from .sqlite_store import connect

# Metric registry: key -> how to pull and treat it. ``additive`` marks metrics
# where summing across trials and cumulating along the X-axis is meaningful
# (tokens, cost, churn); scores/rates are not additive (cumulative is allowed
# but flagged in the UI as unusual).
METRICS: dict[str, dict] = {
    "cost_usd":            {"label": "Cost (USD)",        "expr": "c.cost_usd",                "additive": True},
    "total_tokens":        {"label": "Total tokens",      "expr": "c.total_tokens",            "additive": True},
    "input_tokens":        {"label": "Input tokens",      "expr": "c.input_tokens",            "additive": True},
    "output_tokens":       {"label": "Output tokens",     "expr": "c.output_tokens",           "additive": True},
    "cache_read_tokens":   {"label": "Cache-read tokens", "expr": "c.cache_read_tokens",       "additive": True},
    "cache_write_tokens":  {"label": "Cache-write tokens","expr": "c.cache_write_tokens",      "additive": True},
    "reasoning_tokens":    {"label": "Reasoning tokens",  "expr": "c.reasoning_tokens",        "additive": True},
    "final_score":         {"label": "Final score",       "expr": "r.final_score",             "additive": False},
    "quality_score":       {"label": "Quality score",     "expr": "r.quality_score",           "additive": False},
    "success":             {"label": "Success (1/0)",     "expr": "r.success",                 "additive": False},
    "hidden_pass_rate":    {"label": "Hidden pass rate",  "expr": "r.hidden_pass_rate",        "additive": False},
    "line_churn":          {"label": "Line churn",        "expr": "t.line_churn",              "additive": True},
    "changed_files_total": {"label": "Changed files",     "expr": "t.changed_files_total",     "additive": True},
    "wall_time_seconds":   {"label": "Wall time (s)",     "expr": "r.total_wall_time_seconds", "additive": True},
}

AGGREGATIONS = ("sum", "mean", "median", "all")


def metric_catalog() -> list[dict]:
    """Metrics offered to the UI, with their additivity."""
    return [
        {"key": k, "label": v["label"], "additive": v["additive"]}
        for k, v in METRICS.items()
    ]


def available_conditions(db_path: Path) -> list[str]:
    db_path = Path(db_path)
    if not db_path.exists():
        return []
    conn = connect(db_path)
    try:
        return [
            r["condition_id"]
            for r in conn.execute(
                "SELECT DISTINCT condition_id FROM runs "
                "WHERE condition_id IS NOT NULL ORDER BY condition_id"
            )
        ]
    finally:
        conn.close()


def _rows(conn, metric: str, conditions: list[str] | None) -> list[dict]:
    expr = METRICS[metric]["expr"]
    sql = (
        f"SELECT r.run_id AS run_id, r.condition_id AS condition_id, "
        f"r.task_id AS task_id, {expr} AS value "
        f"FROM runs r "
        f"LEFT JOIN provider_cost c ON c.run_id = r.run_id "
        f"LEFT JOIN telemetry t ON t.run_id = r.run_id "
    )
    params: list = []
    if conditions:
        placeholders = ", ".join("?" for _ in conditions)
        sql += f"WHERE r.condition_id IN ({placeholders}) "
        params = list(conditions)
    sql += "ORDER BY r.run_id ASC"  # run_id is time-prefixed => chronological
    out = []
    for row in conn.execute(sql, params):
        if row["value"] is None:
            continue  # e.g. provider tokens on a run with no cost entered
        out.append(
            {
                "run_id": row["run_id"],
                "condition_id": row["condition_id"],
                "task_id": row["task_id"],
                "value": float(row["value"]),
            }
        )
    return out


def _combine(values: list[float], agg: str) -> float:
    if agg == "sum":
        return float(sum(values))
    if agg == "mean":
        return float(statistics.fmean(values))
    if agg == "median":
        return float(statistics.median(values))
    raise ValueError(f"unknown aggregation: {agg}")


def build_series(
    db_path: Path,
    metric: str,
    *,
    mode: str = "per_test",       # "per_test" | "cumulative"
    conditions: list[str] | None = None,
    x_mode: str = "time",         # "time" (per-series ordinal) | "task" (shared axis)
    agg: str = "sum",             # sum | mean | median | all
) -> dict:
    """Return chart series for ``metric`` grouped by condition.

    ``time``: each condition gets its own sequence ordered by run time; X is the
    1-based test ordinal. ``task``: a shared task axis (ordered by global first
    run time) so series align column-for-column. ``cumulative`` running-sums the
    value along each series' order.
    """
    if metric not in METRICS:
        raise ValueError(f"unknown metric: {metric}")
    if agg not in AGGREGATIONS:
        raise ValueError(f"unknown aggregation: {agg}")

    conn = connect(Path(db_path))
    try:
        rows = _rows(conn, metric, conditions)
    finally:
        conn.close()

    # Group rows by (condition, task) preserving first-seen (chronological) order.
    groups: dict[tuple[str, str], dict] = {}
    for r in rows:
        key = (r["condition_id"], r["task_id"])
        g = groups.setdefault(
            key, {"condition": r["condition_id"], "task_id": r["task_id"],
                  "values": [], "run_ids": [], "first_run": r["run_id"]}
        )
        g["values"].append(r["value"])
        g["run_ids"].append(r["run_id"])

    # Collapse trials per (condition, task) unless agg == "all".
    points: list[dict] = []  # flat list of collapsed points
    for g in groups.values():
        if agg == "all":
            for v, rid in zip(g["values"], g["run_ids"]):
                points.append({"condition": g["condition"], "task_id": g["task_id"],
                               "value": v, "run_ids": [rid], "first_run": rid})
        else:
            points.append({"condition": g["condition"], "task_id": g["task_id"],
                           "value": _combine(g["values"], agg),
                           "run_ids": g["run_ids"], "first_run": g["first_run"]})

    # Shared task ordering (used by x_mode == "task"): tasks by global first run.
    task_first: dict[str, str] = {}
    for p in points:
        if p["task_id"] not in task_first or p["first_run"] < task_first[p["task_id"]]:
            task_first[p["task_id"]] = p["first_run"]
    shared_tasks = sorted(task_first, key=lambda tid: task_first[tid])

    # Bucket points by condition.
    by_cond: dict[str, list[dict]] = {}
    for p in points:
        by_cond.setdefault(p["condition"], []).append(p)

    series: list[dict] = []
    for cond in sorted(by_cond):
        pts = sorted(by_cond[cond], key=lambda p: p["first_run"])
        if x_mode == "task":
            # Align onto the shared task axis (gaps allowed).
            by_task: dict[str, dict] = {}
            for p in pts:
                # if agg == all there can be multiple per task; keep last by time
                by_task[p["task_id"]] = p
            ordered = [(tid, by_task.get(tid)) for tid in shared_tasks]
        else:
            ordered = [(p["task_id"], p) for p in pts]

        running = 0.0
        spoints = []
        for i, (label, p) in enumerate(ordered, start=1):
            if p is None:
                spoints.append({"x": i, "label": label, "task_id": label,
                                "value": None, "run_ids": []})
                continue
            val = p["value"]
            if mode == "cumulative":
                running += val
                y = running
            else:
                y = val
            spoints.append({"x": i, "label": label, "task_id": label,
                            "value": round(y, 6), "run_ids": p["run_ids"]})
        series.append({"condition": cond, "points": spoints})

    return {
        "metric": metric,
        "metric_label": METRICS[metric]["label"],
        "additive": METRICS[metric]["additive"],
        "mode": mode,
        "x_mode": x_mode,
        "agg": agg,
        "x_labels": shared_tasks if x_mode == "task" else None,
        "series": series,
    }
