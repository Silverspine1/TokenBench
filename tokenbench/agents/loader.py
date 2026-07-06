"""Loading of agent adapter JSON configs."""

from __future__ import annotations

import json
from pathlib import Path

from .schema import AgentConfig


class AgentConfigError(Exception):
    """Raised when an agent config cannot be found or parsed."""


def load_agent_config(path: Path) -> AgentConfig:
    """Load and validate a single agent config JSON file."""
    path = Path(path)
    if not path.exists():
        raise AgentConfigError(f"agent config not found: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise AgentConfigError(f"invalid JSON in agent config {path}: {e}") from e
    try:
        return AgentConfig.model_validate(raw)
    except Exception as e:  # pydantic ValidationError
        raise AgentConfigError(f"invalid agent config {path}: {e}") from e


def load_agent(agents_dir: Path, agent_id: str) -> AgentConfig:
    """Resolve ``<agents_dir>/<agent_id>.json`` into an AgentConfig."""
    return load_agent_config(Path(agents_dir) / f"{agent_id}.json")
