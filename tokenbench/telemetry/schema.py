"""Pydantic models describing the telemetry.json artifact.

Telemetry is raw evidence. The schema is intentionally permissive about
provider usage (which may be unavailable today) and deliberately marks every
token count as an estimate.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class TelemetryTiming(BaseModel):
    agent_wall_time_seconds: float
    visible_test_wall_time_seconds: float
    hidden_test_wall_time_seconds: float
    total_wall_time_seconds: float


class TelemetryPrompt(BaseModel):
    prompt_chars: int
    prompt_bytes: int
    prompt_estimated_tokens: int


class TelemetryLogs(BaseModel):
    agent_stdout_bytes: int
    agent_stderr_bytes: int
    visible_stdout_bytes: int
    visible_stderr_bytes: int
    hidden_stdout_bytes: int
    hidden_stderr_bytes: int
    total_log_bytes: int
    estimated_log_tokens: int


class TelemetryPatch(BaseModel):
    changed_files_total: int
    changed_scored_files: int
    changed_ignored_files: int
    changed_forbidden_files: int
    added_files: int
    modified_files: int
    deleted_files: int
    patch_bytes: int
    patch_estimated_tokens: int
    lines_added: int
    lines_deleted: int
    line_churn: int


class TelemetryCommands(BaseModel):
    agent_command: list[str] = Field(default_factory=list)
    visible_commands_run: int
    hidden_commands_run: int
    test_commands_total: int
    dependency_download_events: int
    detected_install_markers: list[str] = Field(default_factory=list)


class TelemetryResults(BaseModel):
    visible_pass_rate: float
    hidden_pass_rate: float
    quality_score: float
    success: bool
    final_score: float


class ProviderUsage(BaseModel):
    """Provider-reported usage. May be unavailable; fields stay null until a
    reliable source is wired in. The shape is fixed now so later parsers can
    populate it without a schema migration."""

    available: bool = False
    source: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    cache_read_tokens: Optional[int] = None
    cache_write_tokens: Optional[int] = None
    reasoning_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    raw: dict[str, Any] = Field(default_factory=dict)


class TelemetryEstimates(BaseModel):
    estimated_total_observed_tokens: int
    token_estimator: str


class TelemetryTokenEstimates(BaseModel):
    """Estimated token breakdown, split by source (input/output/tool/patch).

    These are deterministic ``ceil(chars/4)`` approximations, NOT provider
    accounting. Keep them strictly separate from ``provider_usage`` — confusing
    an estimate for billed usage is the one mistake this split exists to prevent.
    """

    estimator: str

    prompt_input_tokens: int

    agent_stdout_output_tokens: int
    agent_stderr_output_tokens: int
    agent_total_output_tokens: int

    visible_test_output_tokens: int
    hidden_test_output_tokens: int
    tool_test_output_tokens: int

    patch_tokens: int

    total_observed_tokens: int


class Telemetry(BaseModel):
    run_id: str
    repo_id: str
    task_id: str
    condition_id: str = "unspecified"
    agent_id: Optional[str] = None
    trial_index: int = 0

    timing: TelemetryTiming
    prompt: TelemetryPrompt
    logs: TelemetryLogs
    patch: TelemetryPatch
    commands: TelemetryCommands
    results: TelemetryResults
    provider_usage: ProviderUsage
    # Authoritative token breakdown. ``estimates`` is retained as a
    # backward-compatible blended total.
    token_estimates: TelemetryTokenEstimates
    estimates: TelemetryEstimates
