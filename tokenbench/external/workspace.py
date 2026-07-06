"""Workspace materialization for external-repo tasks (patch-overlay model)."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from ..core.hashing import hash_directory
from ..core.ids import utc_now
from ..core.paths import JUNK_DIRS, RunPaths
from .schema import ExternalRepoSource


class ExternalWorkspaceError(RuntimeError):
    """Raised when external workspace setup fails."""


def _ignore_junk(_dir: str, names: list[str]) -> set[str]:
    return {n for n in names if n in JUNK_DIRS}


def _copy_tree(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst, ignore=_ignore_junk)


def _apply_patch(patch_file: Path, workspace: Path) -> None:
    """Apply a unified diff patch inside workspace using git apply."""
    result = subprocess.run(
        ["git", "apply", "--whitespace=nowarn", str(patch_file)],
        cwd=workspace,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        # Try with patch -p1 as fallback
        result2 = subprocess.run(
            ["patch", "-p1", "-i", str(patch_file)],
            cwd=workspace,
            capture_output=True,
            text=True,
        )
        if result2.returncode != 0:
            raise ExternalWorkspaceError(
                f"Failed to apply patch {patch_file}:\n"
                f"git apply stderr: {result.stderr}\n"
                f"patch stderr: {result2.stderr}"
            )


def materialize_external_workspace(
    source: ExternalRepoSource,
    task_dir: Path,
    run_paths: RunPaths,
    overwrite: bool = False,
) -> dict:
    """Copy pinned external repo into workspace and apply defect patch.

    Steps:
      1. Copy (or clone) cached upstream repo at pinned commit.
      2. Apply task defect.patch if present (bug-fix tasks).
      3. Copy visible tests into workspace (under tests_visible/).
      4. Write metadata.json and return it.

    For staged implementation tasks (no defect.patch), step 2 is skipped.
    """
    clone_dir = task_dir.parent.parent / "cache" / ".git_clone"
    if not clone_dir.exists():
        raise ExternalWorkspaceError(
            f"Cached clone not found at {clone_dir}. "
            f"Run: git clone {source.url} {clone_dir}"
        )

    workspace = run_paths.workspace
    if workspace.exists():
        if not overwrite:
            raise ExternalWorkspaceError(
                f"Workspace already exists: {workspace}. Use --overwrite to replace."
            )
        shutil.rmtree(workspace)

    run_paths.ensure_dirs()

    # Step 1: copy pinned repo
    _copy_tree(clone_dir, workspace)

    # Step 2: apply defect patch (bug-fix tasks only)
    defect_patch = task_dir / "defect.patch"
    patch_applied = False
    if defect_patch.exists():
        _apply_patch(defect_patch, workspace)
        patch_applied = True

    # Step 3: copy visible tests into workspace
    visible_tests_src = task_dir / "visible_tests"
    if visible_tests_src.exists() and any(visible_tests_src.iterdir()):
        visible_tests_dst = workspace / "tests_visible"
        if visible_tests_dst.exists():
            shutil.rmtree(visible_tests_dst)
        shutil.copytree(visible_tests_src, visible_tests_dst)

    metadata = {
        "repo_id": source.repo_id,
        "pinned_commit": source.pinned_commit,
        "source_url": source.url,
        "task_dir": task_dir.as_posix(),
        "defect_patch_applied": patch_applied,
        "workspace_path": workspace.as_posix(),
        "workspace_hash": hash_directory(workspace),
        "start_time": utc_now().isoformat(),
    }
    run_paths.metadata.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata
