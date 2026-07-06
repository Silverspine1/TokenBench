"""Manual cost entry endpoint (USD)."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ...manual.service import attach_manual_cost

router = APIRouter()


class CostRequest(BaseModel):
    cost_usd: float | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cache_read_tokens: int | None = None
    cache_write_tokens: int | None = None
    reasoning_tokens: int | None = None
    total_tokens: int | None = None
    source: str = "manual_estimate"
    confidence: str = "low"
    notes: str = ""


@router.post("/runs/{run_id}/cost")
def attach_cost(request: Request, run_id: str, body: CostRequest) -> dict:
    run_dir = Path(request.app.state.runs_root) / run_id
    if not (run_dir / "manual_ide.json").exists():
        raise HTTPException(status_code=404, detail=f"unknown run: {run_id}")
    fields = {
        "cost_usd": body.cost_usd,
        "input_tokens": body.input_tokens,
        "output_tokens": body.output_tokens,
        "cache_read_tokens": body.cache_read_tokens,
        "cache_write_tokens": body.cache_write_tokens,
        "reasoning_tokens": body.reasoning_tokens,
        "total_tokens": body.total_tokens,
    }
    try:
        return attach_manual_cost(
            run_dir, fields, source=body.source, confidence=body.confidence,
            notes=body.notes,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
