"""Pydantic schema for task manifests."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Mode(str, Enum):
    atomic = "atomic"
    batch = "batch"
    sequential = "sequential"


class Category(str, Enum):
    bugfix = "bugfix"
    implementation = "implementation"
    staged_implementation = "staged_implementation"
    contract = "contract"
    reorg = "reorg"
    mixed = "mixed"


class Difficulty(str, Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"
    frontier_hard = "frontier_hard"


class DependencyPolicy(str, Enum):
    preinstalled_only = "preinstalled_only"
    installs_allowed = "installs_allowed"


class StructureContract(BaseModel):
    """Deterministic structure target for a reorg task (V0.7).

    Scored objectively against the candidate workspace: required paths must
    exist, opaque/forbidden paths must be gone (or reduced to thin compatibility
    shims), public entrypoints must survive, and compatibility imports must
    still resolve. No subjective "nice architecture" judgement.
    """

    model_config = {"extra": "forbid"}

    required_paths: list[str] = Field(default_factory=list)
    forbidden_paths: list[str] = Field(default_factory=list)
    compatibility_imports: list[str] = Field(default_factory=list)
    public_entrypoints: list[str] = Field(default_factory=list)
    # A forbidden/opaque file counts as "removed" if deleted OR shrunk to a thin
    # re-export shim no larger than this many bytes.
    shim_max_bytes: int = 400


class OutputStress(BaseModel):
    """Controlled long-output expectation for a task (V0.7).

    When enabled, the doctor measures the visible-test stdout produced on the
    broken snapshot and warns if it falls outside the declared band or exceeds
    the hard 1 MB ceiling.
    """

    model_config = {"extra": "forbid"}

    enabled: bool = False
    expected_visible_output_bytes_min: int = 50000
    expected_visible_output_bytes_max: int = 300000


class RepoKind(str, Enum):
    internal = "internal"
    external_github = "external_github"


class TaskManifest(BaseModel):
    """A single benchmark task definition."""

    model_config = {"extra": "forbid"}

    task_id: str = Field(min_length=1)
    repo_id: str = Field(min_length=1)
    mode: Mode
    category: Category
    difficulty: Difficulty
    prompt: str = Field(min_length=1)

    # --- SWE-bench-style issue framing (V0.5.1) --------------------------
    # When both are set, the agent prompt is rendered as an issue report:
    #   "Issue: <issue_title>\n\n<issue_body>".
    # `prompt` carries the issue body for backward compatibility (older readers
    # and the visible-prompt assertions); authors keep `prompt` == `issue_body`.
    issue_title: str = ""
    issue_body: str = ""
    # Rendered to the agent as an "Expected:" bullet list when non-empty. These
    # are observable behaviours, never root-cause hints.
    expected_behavior: list[str] = Field(default_factory=list)

    # --- V0.7 reorg / staged / output-stress -----------------------------
    structure_contract: StructureContract | None = None
    output_stress: OutputStress | None = None

    # Staged-implementation linkage. A staged task belongs to a stage_group_id
    # and points at its sibling stage. Stage 2 starts from Stage 1's candidate
    # output when input_source == "previous_candidate".
    stage: int | None = None
    stage_group_id: str = ""
    next_stage_task_id: str = ""
    previous_stage_task_id: str = ""
    input_source: str = ""

    # --- V0.9 external-repo fields (optional; set for repo_kind=external_github) ---
    repo_kind: RepoKind = RepoKind.internal
    # Path to benchmark/external_repos/<repo>/source.json (relative to project root)
    source_ref: str = ""
    # Exact SHA of the pinned upstream commit (also in source.json; duplicated for auditability)
    base_commit: str = ""
    # Path to the defect patch relative to the task directory (bug-fix tasks only)
    defect_patch: str = "defect.patch"
    # Path to private author notes relative to the task directory (NEVER rendered to agent)
    private_notes_path: str = "private_notes.json"

    # For internal tasks: path to the broken snapshot directory (relative to project root).
    # Optional so that external tasks (which use defect.patch overlay) can omit it.
    broken_snapshot: str = ""
    gold_snapshot: str = ""

    visible_commands: list[str] = Field(default_factory=list)
    hidden_commands: list[str]

    allowed_runtime_seconds: int
    log_budget_bytes: int = 250000
    allowed_network: bool = False
    dependency_policy: DependencyPolicy = DependencyPolicy.preinstalled_only

    scored_paths: list[str] = Field(default_factory=list)
    ignored_paths: list[str] = Field(default_factory=list)
    forbidden_paths: list[str]

    # --- Optional task-authoring metadata (V0.4) -------------------------
    # For benchmark maintainers, never shown to the agent.
    expected_failure_summary: str = ""
    skills_tested: list[str] = Field(default_factory=list)
    root_cause_files: list[str] = Field(default_factory=list)
    expected_changed_files_min: int | None = None
    expected_changed_files_max: int | None = None
    # Private notes. MUST NOT be included in any agent prompt.
    task_author_notes: str = ""
