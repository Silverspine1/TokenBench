"""Staged carryover orchestration (V0.7).

Runs Stage 1, then runs Stage 2 *on Stage 1's candidate output* as a fresh agent
process, and emits ``staged_score.json``. This deliberately isolates code
maintainability (does Stage 1's design extend cleanly?) from conversation memory
(Stage 2 gets no chat history, only the files).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from ..manifests.schema import TaskManifest
from ..runners.base import AgentRunner
from .scoring import staged_metrics, staged_score


def run_staged_group(
    base: Path,
    stage1_manifest: TaskManifest,
    stage2_manifest: TaskManifest,
    agent_runner: AgentRunner,
    condition_id: str,
    trial_index: int,
    overwrite: bool,
    runs_root: Optional[Path] = None,
    isolated_runs_root: Optional[Path] = None,
    graphify: bool = False,
) -> dict:
    """Run both stages with carryover and return the combined staged report."""
    # Lazy import avoids a cli <-> staged import cycle at module load.
    from ..cli import execute_run

    if stage1_manifest.stage_group_id != stage2_manifest.stage_group_id:
        raise ValueError("stage 1 and stage 2 manifests are not in the same group")

    # --- Stage 1: normal run from its broken snapshot --------------------
    report1 = execute_run(
        stage1_manifest,
        base,
        agent_runner,
        condition_id=condition_id,
        trial_index=trial_index,
        overwrite=overwrite,
        runs_root=runs_root,
        isolated_runs_root=isolated_runs_root,
        quiet=True,
        graphify=graphify,
    )
    stage1_run_dir = base / report1["paths"]["run_dir"]
    stage1_candidate = (stage1_run_dir / "candidate").resolve()

    # --- Stage 2: fresh agent process, starting from Stage 1's candidate -
    report2 = execute_run(
        stage2_manifest,
        base,
        agent_runner,
        condition_id=condition_id,
        trial_index=trial_index,
        overwrite=overwrite,
        runs_root=runs_root,
        isolated_runs_root=isolated_runs_root,
        quiet=True,
        override_snapshot=stage1_candidate,
        graphify=graphify,
    )
    stage2_run_dir = base / report2["paths"]["run_dir"]

    # --- Staged scoring + friction telemetry -----------------------------
    metrics = staged_metrics(stage1_run_dir, stage2_run_dir)
    scored = staged_score(
        stage1_quality=float(report1["quality_score"]),
        stage2_quality=float(report2["quality_score"]),
        friction_ratio=float(metrics["extension_friction"]),
    )

    staged_report = {
        "stage_group_id": stage1_manifest.stage_group_id,
        "condition_id": condition_id,
        "trial_index": trial_index,
        "stage1": {
            "task_id": stage1_manifest.task_id,
            "run_id": report1["run_id"],
            "run_dir": report1["paths"]["run_dir"],
            "quality_score": report1["quality_score"],
            "success": report1["success"],
        },
        "stage2": {
            "task_id": stage2_manifest.task_id,
            "run_id": report2["run_id"],
            "run_dir": report2["paths"]["run_dir"],
            "quality_score": report2["quality_score"],
            "success": report2["success"],
            "previous_run_id": report1["run_id"],
        },
        "staged": {
            "stage_group_id": stage1_manifest.stage_group_id,
            "stage": 2,
            "previous_run_id": report1["run_id"],
            **metrics,
            **scored,
        },
    }

    # Persist beside Stage 2's artifacts.
    (stage2_run_dir / "staged_score.json").write_text(
        json.dumps(staged_report, indent=2), encoding="utf-8"
    )
    return staged_report
