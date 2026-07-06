"""Semantic validation of a manifest beyond schema/type checks."""

from __future__ import annotations

from pathlib import Path

from .schema import TaskManifest


class ManifestValidationError(ValueError):
    """Raised when a manifest is structurally valid but semantically wrong."""


def validate_manifest(manifest: TaskManifest, base_dir: Path) -> list[str]:
    """Return a list of validation error strings. Empty list == valid.

    ``base_dir`` is the root that snapshot paths are resolved against.
    """
    errors: list[str] = []

    if not manifest.task_id.strip():
        errors.append("task_id must be non-empty")
    if not manifest.repo_id.strip():
        errors.append("repo_id must be non-empty")

    from .schema import RepoKind
    if manifest.repo_kind != RepoKind.external_github:
        broken = (base_dir / manifest.broken_snapshot)
        gold = (base_dir / manifest.gold_snapshot)
        if not broken.exists():
            errors.append(f"broken_snapshot does not exist: {broken}")
        if not gold.exists():
            errors.append(f"gold_snapshot does not exist: {gold}")

    if len(manifest.hidden_commands) < 1:
        errors.append("at least one hidden command is required")

    if manifest.allowed_runtime_seconds <= 0:
        errors.append("allowed_runtime_seconds must be positive")

    if len(manifest.forbidden_paths) < 1:
        errors.append("forbidden_paths must not be empty")

    return errors


def assert_valid(manifest: TaskManifest, base_dir: Path) -> None:
    errors = validate_manifest(manifest, base_dir)
    if errors:
        raise ManifestValidationError("; ".join(errors))
