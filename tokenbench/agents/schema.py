"""Pydantic schema for CLI agent adapter configs.

Keep ``command_template`` configurable. The exact Claude/Gemini flags change
over time, so they live in JSON, never baked into Python.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

# Provider the agent's CLI talks to. "unknown" is the backward-compatible
# default for configs predating this field.
SUPPORTED_PROVIDERS = ("claude", "gemini", "dry_run", "local", "unknown")

# How the recorded model string was obtained. "configured" = declared in this
# JSON; "cli_reported" = read back from the CLI; "unknown" = not established.
SUPPORTED_MODEL_RESOLUTIONS = ("configured", "cli_reported", "unknown")


class AgentConfig(BaseModel):
    """A CLI coding agent the harness can launch as a subprocess."""

    model_config = {"extra": "forbid"}

    agent_id: str = Field(min_length=1)
    display_name: str = ""
    kind: str = "cli_agent"
    command_template: list[str] = Field(min_length=1)
    supports_stdin_prompt: bool = True
    supports_workspace_cwd: bool = True
    final_submission_mode: str = "process_exit"
    default_timeout_seconds: int = Field(900, gt=0)
    env: dict[str, str] = Field(default_factory=dict)
    # Telemetry-only metadata. Optional and defaulting to "unknown" so configs
    # written before these fields keep loading unchanged.
    provider: str = "unknown"
    model: str = "unknown"
    model_resolution: str = "configured"

    @field_validator("provider")
    @classmethod
    def _provider_supported(cls, v: str) -> str:
        if v not in SUPPORTED_PROVIDERS:
            raise ValueError(
                f"unsupported provider: {v!r} (allowed: {', '.join(SUPPORTED_PROVIDERS)})"
            )
        return v

    @field_validator("model_resolution")
    @classmethod
    def _model_resolution_supported(cls, v: str) -> str:
        if v not in SUPPORTED_MODEL_RESOLUTIONS:
            raise ValueError(
                f"unsupported model_resolution: {v!r} "
                f"(allowed: {', '.join(SUPPORTED_MODEL_RESOLUTIONS)})"
            )
        return v

    @field_validator("kind")
    @classmethod
    def _kind_supported(cls, v: str) -> str:
        if v != "cli_agent":
            raise ValueError(f"unsupported agent kind: {v!r} (only 'cli_agent' for now)")
        return v

    @field_validator("command_template")
    @classmethod
    def _command_parts_nonempty(cls, v: list[str]) -> list[str]:
        if any(not isinstance(p, str) or p == "" for p in v):
            raise ValueError("command_template entries must be non-empty strings")
        return v

    @field_validator("env")
    @classmethod
    def _env_keys_are_strings(cls, v: dict) -> dict:
        for k in v:
            if not isinstance(k, str):
                raise ValueError("env keys must be strings")
        return v
