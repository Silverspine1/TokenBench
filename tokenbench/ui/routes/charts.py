"""Chart-builder endpoints: metric catalog + computed series from the DB."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request

from ...analysis.charting import (
    available_conditions,
    build_series,
    metric_catalog,
)

router = APIRouter()


def _db_path(request: Request) -> Path:
    return Path(request.app.state.db_path)


@router.get("/charts/options")
def chart_options(request: Request) -> dict:
    """Metrics + conditions available to build a chart."""
    return {
        "metrics": metric_catalog(),
        "conditions": available_conditions(_db_path(request)),
        "modes": ["per_test", "cumulative"],
        "x_modes": ["time", "task"],
        "aggregations": ["sum", "mean", "median", "all"],
    }


@router.get("/charts/data")
def chart_data(
    request: Request,
    metric: str = Query(...),
    mode: str = Query("per_test"),
    x_mode: str = Query("time"),
    agg: str = Query("sum"),
    conditions: str | None = Query(None, description="comma-separated condition_ids"),
) -> dict:
    conds = [c for c in conditions.split(",") if c] if conditions else None
    try:
        return build_series(
            _db_path(request), metric, mode=mode, conditions=conds,
            x_mode=x_mode, agg=agg,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
