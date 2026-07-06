"""Shared run-finalization core.

The second half of an atomic run — archive the candidate, diff it against the
starting snapshot, run visible then hidden tests, persist the raw measured
facts, and score deterministically — factored out of ``cli.execute_run`` so the
manual-IDE service reaches scoring through the *exact same* code path. There is
one scorer, one telemetry writer, one run_state shape; this module is where they
are invoked.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..core.artifacts import (
    compute_file_changes,
    snapshot_candidate,
    write_file_changes,
    write_patch,
)
from ..core.paths import RunPaths
from ..manifests.schema import TaskManifest
from ..runners.base import RunnerResult
from ..scoring.scorer import score_run
from ..scoring.tests import run_hidden_tests, run_visible_tests


def rel_to_base(path: Path, base: Path) -> str:
    """Best-effort path relative to ``base`` as posix; absolute on failure."""
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def finalize_run(
    run_paths: RunPaths,
    manifest: TaskManifest,
    base: Path,
    result: RunnerResult,
    condition_id: str,
    trial_index: int,
    runner_name: str,
    baseline_snapshot: Path,
) -> dict:
    """Archive, diff, test, record, and score one run. Returns the score report.

    ``baseline_snapshot`` is the tree the candidate is diffed against — the
    manifest's broken snapshot for a normal run, or Stage 1's candidate for a
    staged Stage 2. ``result`` carries the agent/operator timing and exit status;
    its byte counts are refreshed from the actual log files here.
    """
    # Refresh agent byte counts from the actual log files (covers manual runs
    # where the runner only touches empty logs).
    result.stdout_bytes = (
        run_paths.agent_stdout.stat().st_size if run_paths.agent_stdout.exists() else 0
    )
    result.stderr_bytes = (
        run_paths.agent_stderr.stat().st_size if run_paths.agent_stderr.exists() else 0
    )

    # Archive candidate + diff against the starting tree. Diffing against the
    # actual starting point makes line-churn measure exactly what this run changed.
    snapshot_candidate(run_paths.workspace, run_paths.candidate)
    baseline_snapshot = baseline_snapshot.resolve()
    file_changes = compute_file_changes(baseline_snapshot, run_paths.candidate, manifest)
    write_file_changes(file_changes, run_paths.file_changes)
    write_patch(baseline_snapshot, run_paths.candidate, run_paths.patch, file_changes)

    # Visible tests, then hidden tests (hidden always run after the agent).
    visible_results = run_visible_tests(
        manifest, base, run_paths.workspace, run_paths.run_dir,
        run_paths.visible_stdout, run_paths.visible_stderr,
    )
    hidden_results = run_hidden_tests(
        manifest, base, run_paths.workspace, run_paths.run_dir,
        run_paths.hidden_stdout, run_paths.hidden_stderr,
    )

    # Persist raw measured facts for deterministic (re)scoring.
    run_state = {
        "run_id": run_paths.run_dir.name,
        "condition_id": condition_id,
        "trial_index": trial_index,
        "runner": runner_name,
        "agent": {
            "exit_code": result.exit_code,
            "started_at": result.started_at,
            "finished_at": result.finished_at,
            "wall_time_seconds": result.wall_time_seconds,
            "final_message": result.final_message,
            "provider_metadata": result.provider_metadata,
            "stdout_bytes": result.stdout_bytes,
            "stderr_bytes": result.stderr_bytes,
            "timed_out": result.timed_out,
        },
        "visible": [r.to_dict() for r in visible_results],
        "hidden": [r.to_dict() for r in hidden_results],
        "paths": {
            "run_dir": rel_to_base(run_paths.run_dir, base),
            "workspace": rel_to_base(run_paths.workspace, base),
            "candidate": rel_to_base(run_paths.candidate, base),
            "patch": rel_to_base(run_paths.patch, base),
            "file_changes": rel_to_base(run_paths.file_changes, base),
        },
    }
    run_paths.run_state.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    # Score deterministically (also writes telemetry.json).
    return score_run(run_paths.run_dir, manifest)
