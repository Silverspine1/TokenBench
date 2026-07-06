"""Result listing endpoints (read-only)."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from ...manual.service import get_run, list_manual_runs

router = APIRouter()


@router.get("/results")
def results(request: Request) -> list[dict]:
    return list_manual_runs(request.app.state.runs_root)


@router.get("/results/{run_id}")
def result_detail(request: Request, run_id: str) -> dict:
    run_dir = Path(request.app.state.runs_root) / run_id
    if not (run_dir / "manual_ide.json").exists():
        raise HTTPException(status_code=404, detail=f"unknown run: {run_id}")
    return get_run(run_dir)
