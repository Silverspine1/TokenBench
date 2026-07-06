"""Bundle export / candidate import endpoints (Mode B)."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel

from ...manual.bundles import export_bundle, import_candidate

router = APIRouter()


class ExportRequest(BaseModel):
    run_id: str


def _run_dir(request: Request, run_id: str) -> Path:
    run_dir = Path(request.app.state.runs_root) / run_id
    if not (run_dir / "manual_ide.json").exists():
        raise HTTPException(status_code=404, detail=f"unknown run: {run_id}")
    return run_dir


@router.post("/bundles/export")
def export(request: Request, body: ExportRequest) -> dict:
    run_dir = _run_dir(request, body.run_id)
    out_zip = run_dir / "bundle.zip"
    try:
        return export_bundle(request.app.state.base, run_dir, out_zip)
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/bundles/import")
async def import_zip(
    request: Request,
    run_id: str = Form(...),
    file: UploadFile = File(...),
) -> dict:
    run_dir = _run_dir(request, run_id)
    tmp = Path(tempfile.mkdtemp(prefix="tokenbench-upload-"))
    zip_path = tmp / "candidate.zip"
    try:
        with zip_path.open("wb") as fh:
            shutil.copyfileobj(file.file, fh)
        return import_candidate(request.app.state.base, run_dir, zip_path)
    except ValueError as e:  # unsafe zip / traversal
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
