"""Pydantic models describing the score.json output."""

from __future__ import annotations

from pydantic import BaseModel


class PhaseCounts(BaseModel):
    commands_total: int
    commands_passed: int


class PhaseTestCounts(BaseModel):
    tests_total: int
    tests_passed: int
    tests_failed: int
    tests_skipped: int
    pass_rate: float


class QualityComponents(BaseModel):
    hidden_test_pass_rate: float
    visible_test_pass_rate: float
    artifact_integrity_score: float


class EfficiencyComponents(BaseModel):
    wall_time_score: float
    log_volume_score: float
    file_churn_score: float
    dependency_score: float


class StructureComponents(BaseModel):
    """Deterministic reorg structure-contract sub-scores (V0.7)."""

    required_paths_score: float
    forbidden_paths_score: float
    public_entrypoint_score: float
    compatibility_score: float
    structure_contract_score: float


class Penalties(BaseModel):
    forbidden_path_modified: bool
    visible_failed_hidden_passed: bool
    dependency_download_events: int
    timed_out: bool


class Timing(BaseModel):
    agent_wall_time_seconds: float
    visible_test_wall_time_seconds: float
    hidden_test_wall_time_seconds: float
    total_wall_time_seconds: float


class UsageProxy(BaseModel):
    agent_stdout_bytes: int
    agent_stderr_bytes: int
    visible_stdout_bytes: int
    visible_stderr_bytes: int
    hidden_stdout_bytes: int
    hidden_stderr_bytes: int
    total_log_bytes: int


class ScorePaths(BaseModel):
    run_dir: str
    workspace: str
    candidate: str
    patch: str
    file_changes: str


class SuccessPolicy(BaseModel):
    """Thresholds that define a successful run. Recorded alongside the flag."""

    quality_threshold: float = 80.0
    hidden_pass_rate_threshold: float = 0.9


class ScoreReport(BaseModel):
    run_id: str
    condition_id: str = "unspecified"
    trial_index: int = 0
    repo_id: str
    task_id: str
    mode: str
    category: str
    difficulty: str
    runner: str
    success: bool
    success_policy: SuccessPolicy
    quality_score: float
    efficiency_score: float
    # Backward-compatible alias for efficiency_score; both are provisional.
    efficiency_proxy_score: float
    # Label marking the efficiency number as a proxy, not a final formula.
    efficiency_score_kind: str = "proxy_v0_2"
    efficiency_gated: float
    final_score: float
    quality_components: QualityComponents
    # Present only for reorg tasks carrying a structure contract; otherwise null.
    structure_components: StructureComponents | None = None
    efficiency_components: EfficiencyComponents
    visible: PhaseCounts
    hidden: PhaseCounts
    visible_tests: PhaseTestCounts
    hidden_tests: PhaseTestCounts
    penalties: Penalties
    timing: Timing
    usage_proxy: UsageProxy
    paths: ScorePaths
    # Link to the raw telemetry artifact written beside score.json.
    telemetry_path: str = "telemetry.json"
