"""Workspace materialization from a broken snapshot."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from ..manifests.schema import TaskManifest
from .hashing import hash_directory
from .ids import utc_now
from .paths import JUNK_DIRS, RunPaths


class WorkspaceExistsError(RuntimeError):
    """Raised when a workspace already exists and overwrite was not requested."""


def _ignore_junk(_dir: str, names: list[str]) -> set[str]:
    return {n for n in names if n in JUNK_DIRS}


def copy_tree(src: Path, dst: Path) -> None:
    """Copy ``src`` into ``dst`` (which must not exist), skipping junk dirs."""
    shutil.copytree(src, dst, ignore=_ignore_junk)


def materialize_workspace(
    manifest: TaskManifest,
    run_paths: RunPaths,
    base_dir: Path,
    overwrite: bool = False,
    override_snapshot: Path | None = None,
) -> dict:
    """Copy a source snapshot into ``run_dir/workspace`` and write metadata.

    By default the source is the manifest's broken snapshot. ``override_snapshot``
    points the materialization at a different tree instead — used by the staged
    runner to start Stage 2 from Stage 1's candidate output. The source snapshot
    is never modified. Returns the metadata dict.
    """
    src = (override_snapshot or (base_dir / manifest.broken_snapshot)).resolve()
    workspace = run_paths.workspace

    if workspace.exists():
        if not overwrite:
            raise WorkspaceExistsError(
                f"Workspace already exists: {workspace}. Use --overwrite to replace."
            )
        shutil.rmtree(workspace)

    run_paths.ensure_dirs()
    copy_tree(src, workspace)

    metadata = {
        "task_id": manifest.task_id,
        "repo_id": manifest.repo_id,
        "mode": manifest.mode.value,
        "category": manifest.category.value,
        "difficulty": manifest.difficulty.value,
        "source_snapshot_path": src.as_posix(),
        "source_snapshot_hash": hash_directory(src),
        "workspace_path": workspace.as_posix(),
        "start_time": utc_now().isoformat(),
    }
    run_paths.metadata.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata
