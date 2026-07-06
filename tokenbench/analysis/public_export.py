"""Build the static public-site payload (``results.json``) from the results DB.

The public TokenBench site is pure static files on S3/CloudFront; this module is
the only thing that touches the database for it. It produces one JSON document
with two leaderboards (cost-saving and quality) plus per-metric chart series, so
the front-end draws everything client-side with no live backend.

Leaderboard math lives here (not in JS) so it is testable and matches the
harness's own numbers. ``build_series`` is reused verbatim for the chart page.
"""

from __future__ import annotations

import statistics
from pathlib import Path

from .charting import METRICS, build_series
from .sqlite_store import connect

# Metrics offered on the per-task explorer chart.
CHART_METRICS = (
    "cost_usd",
    "wall_time_seconds",
    "line_churn",
    "total_tokens",
    "hidden_pass_rate",
    "quality_score",
)


def _condition_rows(conn) -> list[dict]:
    """One aggregated row per condition over all of its scored runs.

    Cost figures only count runs that actually carry provider cost
    (``available = 1``); quality/wall figures count every scored run.
    """
    rows = list(
        conn.execute(
            """
            SELECT r.condition_id AS condition_id,
                   r.run_id       AS run_id,
                   r.task_id      AS task_id,
                   r.quality_score AS quality_score,
                   r.final_score   AS final_score,
                   r.success       AS success,
                   r.total_wall_time_seconds AS wall,
                   c.available     AS cost_available,
                   c.cost_usd      AS cost_usd,
                   c.total_tokens  AS total_tokens
            FROM runs r
            LEFT JOIN provider_cost c ON c.run_id = r.run_id
            WHERE r.condition_id IS NOT NULL
            """
        )
    )

    by_cond: dict[str, dict] = {}
    for row in rows:
        cond = row["condition_id"]
        g = by_cond.setdefault(
            cond,
            {
                "condition": cond,
                "tasks": set(),
                "cost_tasks": set(),
                "runs": 0,
                "quality": [],
                "final": [],
                "success": [],
                "wall": [],
                "cost_total": 0.0,
                "tokens_total": 0,
                "cost_runs": 0,
            },
        )
        g["runs"] += 1
        g["tasks"].add(row["task_id"])
        if row["quality_score"] is not None:
            g["quality"].append(float(row["quality_score"]))
        if row["final_score"] is not None:
            g["final"].append(float(row["final_score"]))
        if row["success"] is not None:
            g["success"].append(float(row["success"]))
        if row["wall"] is not None:
            g["wall"].append(float(row["wall"]))
        if row["cost_available"] and row["cost_usd"] is not None:
            g["cost_total"] += float(row["cost_usd"])
            g["cost_runs"] += 1
            g["cost_tasks"].add(row["task_id"])
            if row["total_tokens"] is not None:
                g["tokens_total"] += int(row["total_tokens"])
    return list(by_cond.values())


def _mean(xs: list[float]) -> float | None:
    return round(statistics.fmean(xs), 4) if xs else None


def _pick_baseline(conds: list[dict], explicit: str | None) -> str | None:
    """Baseline for savings %: explicit > a ``*base*`` condition > priciest.

    Falling back to the priciest condition means every other row shows a
    positive saving, which reads sensibly when no obvious base exists.
    """
    names = [c["condition"] for c in conds]
    if explicit and explicit in names:
        return explicit
    named = [n for n in names if "base" in n.lower()]
    if named:
        return sorted(named)[0]
    priced = [c for c in conds if c["cost_runs"]]
    if priced:
        return max(priced, key=lambda c: c["cost_total"] / max(len(c["cost_tasks"]), 1))["condition"]
    return names[0] if names else None


def _leaderboards(conds: list[dict], baseline: str | None) -> dict:
    base = next((c for c in conds if c["condition"] == baseline), None)
    base_cpt = None
    if base and base["cost_runs"]:
        base_cpt = base["cost_total"] / max(len(base["cost_tasks"]), 1)

    cost_rows = []
    for c in conds:
        if not c["cost_runs"]:
            continue
        cpt = c["cost_total"] / max(len(c["cost_tasks"]), 1)
        savings = None
        if base_cpt and base_cpt > 0:
            savings = round((base_cpt - cpt) / base_cpt * 100.0, 1)
        cost_rows.append(
            {
                "condition": c["condition"],
                "is_baseline": c["condition"] == baseline,
                "cost_total": round(c["cost_total"], 4),
                "cost_per_task": round(cpt, 4),
                "tokens_total": c["tokens_total"],
                "savings_pct": savings,
                "tasks": len(c["cost_tasks"]),
                "runs": c["cost_runs"],
            }
        )
    # Cheapest per task first (best saving on top).
    cost_rows.sort(key=lambda r: r["cost_per_task"])

    quality_rows = []
    for c in conds:
        q = _mean(c["quality"])
        cpt = (c["cost_total"] / max(len(c["cost_tasks"]), 1)) if c["cost_runs"] else None
        # Value = quality earned per dollar spent. This is the cost-to-quality
        # figure that replaces the token-based final score (which conflated
        # observed-token telemetry into the headline number).
        value = round(q / cpt, 1) if (q is not None and cpt and cpt > 0) else None
        quality_rows.append(
            {
                "condition": c["condition"],
                "quality_score": q,
                "value_per_usd": value,
                "success_rate": (round(_mean(c["success"]) * 100.0, 1)
                                 if c["success"] else None),
                "tasks": len(c["tasks"]),
                "runs": c["runs"],
            }
        )
    # Best value first (quality per $); rows without cost sink to the bottom.
    quality_rows.sort(key=lambda r: (r["value_per_usd"] is not None, r["value_per_usd"] or 0.0),
                      reverse=True)

    return {"cost": cost_rows, "quality": quality_rows}


def _suggestions(cost_rows: list[dict], quality_rows: list[dict]) -> list[dict]:
    """Three at-a-glance picks: best value, cheapest, highest quality."""
    out = []
    valued = [r for r in quality_rows if r.get("value_per_usd")]
    if valued:
        b = max(valued, key=lambda r: r["value_per_usd"])
        out.append({"pick": "Best value", "condition": b["condition"],
                    "detail": f"{rnum0(b['value_per_usd'])} quality per $"})
    if cost_rows:
        c = cost_rows[0]
        out.append({"pick": "Cheapest", "condition": c["condition"],
                    "detail": f"${c['cost_per_task']:.3f} per task"})
    q_have = [r for r in quality_rows if r["quality_score"] is not None]
    top_q = max(q_have, key=lambda r: r["quality_score"]) if q_have else None
    if top_q:
        out.append({"pick": "Highest quality", "condition": top_q["condition"],
                    "detail": f"quality {top_q['quality_score']:.1f}"})
    return out


def rnum0(x: float) -> str:
    return f"{x:,.0f}"


def _chart_data(db_path: Path, conditions: list[str]) -> dict:
    data = {}
    for key in CHART_METRICS:
        additive = METRICS[key]["additive"]
        series = build_series(
            db_path,
            key,
            mode="per_test",
            conditions=conditions or None,
            x_mode="task",            # shared task axis so conditions line up
            agg="sum" if additive else "mean",
        )
        data[key] = series
    return data


def build_public_payload(
    db_path: Path,
    *,
    baseline: str | None = None,
    generated_at: str | None = None,
    exclude: tuple[str, ...] = ("headroom",),
) -> dict:
    """Assemble the full ``results.json`` payload for the static site.

    ``generated_at`` is passed through verbatim (stamp it from the caller; the
    DB has no clock). ``baseline`` names the cost-savings reference condition.
    ``exclude`` drops any condition whose id contains one of these substrings
    (default: ``headroom`` — that run failed and is not published).
    """
    db_path = Path(db_path)
    conn = connect(db_path)
    try:
        conds = _condition_rows(conn)
    finally:
        conn.close()

    ex = tuple(x.lower() for x in exclude)
    conds = [c for c in conds if not any(x in c["condition"].lower() for x in ex)]

    names = sorted(c["condition"] for c in conds)
    base = _pick_baseline(conds, baseline)
    boards = _leaderboards(conds, base)
    return {
        "generated_at": generated_at,
        "baseline": base,
        "conditions": names,
        "leaderboards": boards,
        "suggestions": _suggestions(boards["cost"], boards["quality"]),
        "charts": {
            "metrics": [
                {"key": k, "label": METRICS[k]["label"], "additive": METRICS[k]["additive"]}
                for k in CHART_METRICS
            ],
            "data": _chart_data(db_path, names),
        },
    }
