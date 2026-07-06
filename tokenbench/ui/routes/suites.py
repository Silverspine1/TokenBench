"""Suite / task / condition listing endpoints (read-only)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ..registry import list_conditions, list_suites, suite_tasks

router = APIRouter()


@router.get("/suites")
def get_suites(request: Request) -> list[dict]:
    return list_suites(request.app.state.base)


@router.get("/suites/{suite_id}/tasks")
def get_suite_tasks(request: Request, suite_id: str) -> list[dict]:
    rows = suite_tasks(request.app.state.base, suite_id)
    if rows is None:
        raise HTTPException(status_code=404, detail=f"unknown suite: {suite_id}")
    return rows


@router.get("/conditions")
def get_conditions(request: Request) -> list[dict]:
    return list_conditions(request.app.state.base)
