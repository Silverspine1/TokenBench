"""Database admin endpoints: browse / edit / delete ingested run rows.

Edits and deletes act on the SQLite mirror only, never on the run files on disk.
A rebuild re-ingests from ``runs/`` and will overwrite manual edits — that is by
design: the JSON artifacts remain the source of truth.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ...analysis.sqlite_store import (
    delete_row,
    fetch_rows,
    ingest_runs,
    list_tables,
    update_row,
)

router = APIRouter()


def _db_path(request: Request) -> Path:
    return Path(request.app.state.db_path)


class UpdateRequest(BaseModel):
    table: str
    run_id: str
    updates: dict


class DeleteRequest(BaseModel):
    table: str
    run_id: str


@router.get("/db/tables")
def db_tables(request: Request) -> list[dict]:
    return list_tables(_db_path(request))


@router.get("/db/{table}")
def db_rows(request: Request, table: str, limit: int = 500, offset: int = 0) -> dict:
    try:
        return fetch_rows(_db_path(request), table, limit=limit, offset=offset)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/db/update")
def db_update(request: Request, body: UpdateRequest) -> dict:
    try:
        changed = update_row(_db_path(request), body.table, body.run_id, body.updates)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"changed": changed}


@router.post("/db/delete")
def db_delete(request: Request, body: DeleteRequest) -> dict:
    try:
        deleted = delete_row(_db_path(request), body.table, body.run_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"deleted": deleted}


@router.post("/db/rebuild")
def db_rebuild(request: Request) -> dict:
    """Re-ingest all runs into the DB (overwrites manual edits)."""
    return ingest_runs(request.app.state.runs_root, _db_path(request))
