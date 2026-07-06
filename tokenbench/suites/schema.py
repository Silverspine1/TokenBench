"""Pydantic schema for run suites."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Suite(BaseModel):
    """A named set of task manifests to run together."""

    model_config = {"extra": "forbid"}

    suite_id: str = Field(min_length=1)
    description: str = ""
    tasks: list[str] = Field(min_length=1)
    required_trials: int = Field(default=1, ge=1)
    official: bool = False
