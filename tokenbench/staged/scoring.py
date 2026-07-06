"""Deterministic staged-implementation scoring + extension-friction metrics.

Pure functions: given the two stages' run artifacts (or raw numbers), produce
the staged score. ``extension_friction`` is the headline signal — how much of
Stage 1 had to be churned to land Stage 2.
"""

from __future__ import annotations

import json
from pathlib import Path


def extension_friction_score(friction_ratio: float) -> float:
    """Band the friction ratio into a [0, 100] score (lower churn => higher).

    <=1.0 -> 100, <=2.0 -> 80, <=4.0 -> 60, else 30.
    """
    if friction_ratio <= 1.0:
        return 100.0
    if friction_ratio <= 2.0:
        return 80.0
    if friction_ratio <= 4.0:
        return 60.0
    return 30.0


def staged_score(
    stage1_quality: float,
    stage2_quality: float,
    friction_ratio: float,
) -> dict:
    """Compose the staged score from the two stage qualities and friction.

        staged_score = 0.30*stage1_quality + 0.45*stage2_quality
                     + 0.25*extension_friction_score

    A Stage 2 that did not really land (quality < 80) cannot earn more than 50
    on the friction term — cheap churn on a broken extension is not a win.
    """
    efs = extension_friction_score(friction_ratio)
    if stage2_quality < 80.0:
        efs = min(efs, 50.0)
    total = 0.30 * stage1_quality + 0.45 * stage2_quality + 0.25 * efs
    return {
        "stage1_quality": round(stage1_quality, 4),
        "stage2_quality": round(stage2_quality, 4),
        "friction_ratio": round(friction_ratio, 4),
        "extension_friction_score": round(efs, 4),
        "staged_score": round(max(0.0, min(100.0, total)), 4),
    }


def _load_json(path: Path) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _changed_set(file_changes: dict) -> set[str]:
    return (
        set(file_changes.get("added", []))
        | set(file_changes.get("modified", []))
        | set(file_changes.get("deleted", []))
    )


def staged_metrics(stage1_run_dir: Path, stage2_run_dir: Path) -> dict:
    """Compute extension-friction telemetry from the two stages' run dirs."""
    s1_tel = _load_json(Path(stage1_run_dir) / "telemetry.json")
    s2_tel = _load_json(Path(stage2_run_dir) / "telemetry.json")
    s1_changes = _load_json(Path(stage1_run_dir) / "file_changes.json")
    s2_changes = _load_json(Path(stage2_run_dir) / "file_changes.json")

    s1_patch = s1_tel.get("patch", {})
    s2_patch = s2_tel.get("patch", {})

    stage1_line_churn = int(s1_patch.get("line_churn", 0))
    stage2_line_churn = int(s2_patch.get("line_churn", 0))

    s1_set = _changed_set(s1_changes)
    s2_set = _changed_set(s2_changes)
    touched = sorted(s2_set & s1_set)

    friction_ratio = stage2_line_churn / max(stage1_line_churn, 1)

    return {
        "stage1_changed_files": int(s1_patch.get("changed_files_total", len(s1_set))),
        "stage1_line_churn": stage1_line_churn,
        "stage2_changed_files": int(s2_patch.get("changed_files_total", len(s2_set))),
        "stage2_line_churn": stage2_line_churn,
        "stage2_rewrite_ratio": round(friction_ratio, 4),
        "stage2_touched_stage1_files": len(touched),
        "stage2_touched_stage1_file_list": touched,
        "stage2_new_files": int(s2_patch.get("added_files", 0)),
        "stage2_public_interface_breaks": int(
            s2_patch.get("changed_forbidden_files", 0)
        ),
        "stage2_patch_tokens": int(s2_patch.get("patch_estimated_tokens", 0)),
        "extension_friction": round(friction_ratio, 4),
    }
