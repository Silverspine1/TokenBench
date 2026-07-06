"""Leak firewall: the single source of truth for what an operator may see.

A manual run shows the operator a task to solve, exactly as a real agent would
see it — never the answer. This module owns the whitelist of manifest fields
safe to render or bundle, and refuses everything else. The agent-facing prompt
is built by ``runners.prompt_builder.build_prompt``, which already excludes
hidden commands; we reuse it rather than re-deriving a prompt here.
"""

from __future__ import annotations

from pathlib import Path

from ..manifests.schema import TaskManifest
from ..runners.prompt_builder import build_prompt

# Manifest fields safe to expose to the operator / external IDE. Anything not
# listed here is treated as private. Built as an explicit allowlist (never
# ``model_dump``) so a new private field added to the schema is private by
# default — it can only leak if someone deliberately adds it here.
PUBLIC_MANIFEST_FIELDS = (
    "task_id",
    "repo_id",
    "mode",
    "category",
    "difficulty",
    "allowed_runtime_seconds",
    "dependency_policy",
    "allowed_network",
    "visible_commands",
    "forbidden_paths",
    "issue_title",
    "issue_body",
    "expected_behavior",
    "prompt",
)

# Fields that must NEVER appear in a prompt, page, or bundle. Kept explicit so a
# test can assert the firewall stays exhaustive against the schema.
PRIVATE_MANIFEST_FIELDS = (
    "hidden_commands",
    "gold_snapshot",
    "broken_snapshot",
    "scored_paths",
    "ignored_paths",
    "structure_contract",
    "output_stress",
    "expected_failure_summary",
    "skills_tested",
    "root_cause_files",
    "expected_changed_files_min",
    "expected_changed_files_max",
    "task_author_notes",
)


def _enum_value(v):
    return v.value if hasattr(v, "value") else v


def public_manifest(manifest: TaskManifest) -> dict:
    """Return only the operator-safe manifest fields as a JSON-able dict."""
    out: dict = {}
    for field in PUBLIC_MANIFEST_FIELDS:
        out[field] = _enum_value(getattr(manifest, field))
    return out


def safe_prompt(manifest: TaskManifest, workspace_path: Path) -> str:
    """The operator-facing task prompt — identical to the agent prompt."""
    return build_prompt(manifest, Path(workspace_path))
