"""Manual run lifecycle endpoints: start, inspect, prompt, submit, re-score."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ...manifests.schema import TaskManifest
from ...manual.service import create_manual_run, get_run, submit_manual_run
from ...scoring.scorer import score_run
from ..registry import load_task

router = APIRouter()


class StartRequest(BaseModel):
    task_rel: str
    condition_id: str = "manual_generic_ide"
    ide_name: str = ""
    ide_version: str | None = None
    model_name: str = "user-entered"
    operator_notes: str = ""


def _run_dir(request: Request, run_id: str) -> Path:
    run_dir = Path(request.app.state.runs_root) / run_id
    if not (run_dir / "manual_ide.json").exists():
        raise HTTPException(status_code=404, detail=f"unknown run: {run_id}")
    return run_dir


@router.post("/runs/manual/start")
def start_run(request: Request, body: StartRequest) -> dict:
    base = request.app.state.base
    try:
        manifest = load_task(base, body.task_rel)
    except Exception as e:  # bad/unknown task path
        raise HTTPException(status_code=400, detail=f"bad task_rel: {e}")
    return create_manual_run(
        base,
        manifest,
        condition_id=body.condition_id,
        ide_name=body.ide_name,
        ide_version=body.ide_version,
        model_name=body.model_name,
        operator_notes=body.operator_notes,
        runs_root=request.app.state.runs_root,
    )


@router.get("/runs/{run_id}")
def run_detail(request: Request, run_id: str) -> dict:
    return get_run(_run_dir(request, run_id))


@router.get("/runs/{run_id}/prompt")
def run_prompt(request: Request, run_id: str) -> dict:
    run_dir = _run_dir(request, run_id)
    prompt_path = run_dir / "prompt.txt"
    text = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""
    return {"run_id": run_id, "prompt": text}


@router.post("/runs/{run_id}/submit")
def run_submit(request: Request, run_id: str) -> dict:
    run_dir = _run_dir(request, run_id)
    return submit_manual_run(request.app.state.base, run_dir)


@router.post("/runs/{run_id}/score")
def run_score(request: Request, run_id: str) -> dict:
    """Recompute score.json from stored artifacts (run must be submitted first)."""
    run_dir = _run_dir(request, run_id)
    if not (run_dir / "run_state.json").exists():
        raise HTTPException(status_code=409, detail="run not submitted yet")
    manifest = TaskManifest.model_validate_json(
        (run_dir / "task_manifest.json").read_text(encoding="utf-8")
    )
    return score_run(run_dir, manifest)
