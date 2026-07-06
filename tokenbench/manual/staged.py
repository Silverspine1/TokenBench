"""Manual staged carryover: Stage 2 starts from Stage 1's *candidate* output.

Mirrors ``staged.runner.run_staged_group`` but for two manual runs that happen
at different times. Stage 1 is a normal manual run; Stage 2 is created from
Stage 1's frozen candidate tree (not gold, not the accepted solution), so it
measures whether the operator's Stage 1 design extends cleanly. After both are
submitted, ``finalize_staged_group`` writes ``staged_score.json`` beside Stage 2.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from ..manifests.schema import TaskManifest
from ..staged.scoring import staged_metrics, staged_score
from .service import _read_manual_ide, create_manual_run


def create_stage2_manual(
    base: Path,
    stage1_run_dir: Path,
    stage2_manifest: TaskManifest,
    *,
    condition_id: Optional[str] = None,
    ide_name: str = "",
    model_name: str = "user-entered",
    runs_root: Optional[Path] = None,
    overwrite: bool = False,
) -> dict:
    """Create a Stage 2 manual run seeded with Stage 1's candidate tree."""
    base = Path(base)
    stage1_run_dir = Path(stage1_run_dir)
    stage1_record = _read_manual_ide(stage1_run_dir)
    stage1_candidate = (stage1_run_dir / "candidate").resolve()
    if not stage1_candidate.exists():
        raise FileNotFoundError(
            f"Stage 1 has no candidate yet — submit Stage 1 first: {stage1_candidate}"
        )

    return create_manual_run(
        base,
        stage2_manifest,
        condition_id=condition_id or stage1_record.get("condition_id", "unspecified"),
        ide_name=ide_name or stage1_record.get("ide_name", ""),
        model_name=model_name,
        runs_root=runs_root,
        overwrite=overwrite,
        override_snapshot=stage1_candidate,
        mode="local_workspace",
        stage=2,
        stage_group_id=stage2_manifest.stage_group_id,
        previous_run_id=stage1_record.get("run_id", stage1_run_dir.name),
    )


def finalize_staged_group(stage1_run_dir: Path, stage2_run_dir: Path) -> dict:
    """Compute the staged report from two submitted manual runs; persist it."""
    stage1_run_dir = Path(stage1_run_dir)
    stage2_run_dir = Path(stage2_run_dir)

    def _score(run_dir: Path) -> dict:
        return json.loads((run_dir / "score.json").read_text(encoding="utf-8"))

    s1 = _score(stage1_run_dir)
    s2 = _score(stage2_run_dir)

    metrics = staged_metrics(stage1_run_dir, stage2_run_dir)
    scored = staged_score(
        stage1_quality=float(s1["quality_score"]),
        stage2_quality=float(s2["quality_score"]),
        friction_ratio=float(metrics["extension_friction"]),
    )

    s1_rec = _read_manual_ide(stage1_run_dir)
    s2_rec = _read_manual_ide(stage2_run_dir)
    report = {
        "stage_group_id": s2_rec.get("stage_group_id", ""),
        "condition_id": s2.get("condition_id", "unspecified"),
        "trial_index": 0,
        "stage1": {
            "task_id": s1["task_id"],
            "run_id": s1["run_id"],
            "quality_score": s1["quality_score"],
            "success": s1["success"],
        },
        "stage2": {
            "task_id": s2["task_id"],
            "run_id": s2["run_id"],
            "quality_score": s2["quality_score"],
            "success": s2["success"],
            "previous_run_id": s1_rec.get("run_id", stage1_run_dir.name),
        },
        "staged": {
            "stage": 2,
            "previous_run_id": s1_rec.get("run_id", stage1_run_dir.name),
            **metrics,
            **scored,
        },
    }
    (stage2_run_dir / "staged_score.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report
