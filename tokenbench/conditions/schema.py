"""Pydantic schema for benchmark run conditions."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Condition(BaseModel):
    """A named run condition (agent + model + tools) recorded on every run."""

    model_config = {"extra": "forbid"}

    condition_id: str = Field(min_length=1)
    agent: str = Field(min_length=1)
    model: str = Field(min_length=1)
    tools: list[str] = Field(default_factory=list)
    description: str = ""
    cost_basis: str = "provider_reported"
    official: bool = False
